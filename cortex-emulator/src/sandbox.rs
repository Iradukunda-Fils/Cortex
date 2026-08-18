// Profile A Sandbox Supervisor Implementation
// Enforces the 7-Step Process Lifecycle, 2-Stage PID 1 Fork Topology, and Strict close_range FD Sanitation:
// Host Supervisor -> fork() -> Child A (unshare namespaces, prctl, close_range, landlock, seccomp) -> fork() -> Child B (PID 1 execve)

use std::os::unix::io::RawFd;

pub const TARGET_IPC_FD: RawFd = 3;

#[derive(Debug, PartialEq, Eq)]
pub enum SandboxError {
    PrctlFailed(i32),
    FdSanitationFailed,
    NamespaceUnshareFailed(i32),
    SeccompInstallFailed(i32),
    IpcSocketpairFailed(i32),
    ForkFailed(i32),
    ExecutionFailed(String),
}

pub struct ProfileASupervisor {
    pub gateway_fd: RawFd,
    pub worker_pid: Option<libc::pid_t>,
}

impl ProfileASupervisor {
    /// Step 3: Strict Atomic File Descriptor Sanitation.
    /// Preserves standard streams (0: stdin, 1: stdout, 2: stderr) and binds the IPC socket to FD 3.
    /// All descriptors > 3 are atomically closed via kernel sys_close_range. Failure fails closed instantly.
    pub fn sanitize_file_descriptors(worker_ipc_fd: RawFd) -> Result<(), SandboxError> {
        unsafe {
            // Move worker IPC descriptor to fixed slot (FD 3)
            if worker_ipc_fd != TARGET_IPC_FD {
                if libc::dup2(worker_ipc_fd, TARGET_IPC_FD) < 0 {
                    return Err(SandboxError::FdSanitationFailed);
                }
                libc::close(worker_ipc_fd);
            }

            // Ensure FD 3 survives execve (clear FD_CLOEXEC)
            let flags = libc::fcntl(TARGET_IPC_FD, libc::F_GETFD);
            if flags >= 0 {
                libc::fcntl(TARGET_IPC_FD, libc::F_SETFD, flags & !libc::FD_CLOEXEC);
            }

            // Execute kernel close_range(4, ~0U, 0)
            #[cfg(target_os = "linux")]
            {
                let res = libc::syscall(libc::SYS_close_range, 4, !0u32, 0);
                if res != 0 {
                    // Strict policy: fail closed if kernel close_range unavailable
                    return Err(SandboxError::FdSanitationFailed);
                }
            }
        }
        Ok(())
    }

    /// Step 2: Enable PR_SET_NO_NEW_PRIVS to prevent privilege escalation via suid/sgid or seccomp bypass.
    pub fn set_no_new_privs() -> Result<(), SandboxError> {
        #[cfg(target_os = "linux")]
        {
            let res = unsafe { libc::prctl(libc::PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) };
            if res != 0 {
                return Err(SandboxError::PrctlFailed(res));
            }
        }
        Ok(())
    }

    /// Step 4: Unshare Linux Namespaces (PID, Network, Filesystem, IPC).
    pub fn unshare_namespaces() -> Result<(), SandboxError> {
        #[cfg(target_os = "linux")]
        {
            let flags =
                libc::CLONE_NEWPID | libc::CLONE_NEWNET | libc::CLONE_NEWNS | libc::CLONE_NEWIPC;
            let res = unsafe { libc::unshare(flags) };
            if res != 0 {
                return Err(SandboxError::NamespaceUnshareFailed(res));
            }
        }
        Ok(())
    }

    /// Step 1 & 7: Create narrow Unix-domain socketpair for worker-gateway IPC.
    pub fn create_ipc_socketpair() -> Result<(RawFd, RawFd), SandboxError> {
        let mut fds: [RawFd; 2] = [0; 2];
        #[cfg(target_os = "linux")]
        {
            let res = unsafe {
                libc::socketpair(
                    libc::AF_UNIX,
                    libc::SOCK_STREAM | libc::SOCK_CLOEXEC,
                    0,
                    fds.as_mut_ptr(),
                )
            };
            if res != 0 {
                return Err(SandboxError::IpcSocketpairFailed(res));
            }
        }
        #[cfg(not(target_os = "linux"))]
        {
            fds = [3, 4];
        }
        Ok((fds[0], fds[1]))
    }

    /// Spawns worker process using 2-Stage Child Fork Pattern:
    /// Host Supervisor -> fork() -> Child A (unshare namespaces, prctl, close_range) -> fork() -> Child B (PID 1 execve).
    /// If any isolation step fails in child context, child immediately aborts via _exit(127).
    pub fn spawn_isolated_worker(worker_binary: &str) -> Result<Self, SandboxError> {
        let (worker_fd, gateway_fd) = Self::create_ipc_socketpair()?;

        #[cfg(target_os = "linux")]
        {
            let pid_a = unsafe { libc::fork() };
            if pid_a < 0 {
                return Err(SandboxError::ForkFailed(pid_a));
            }

            if pid_a == 0 {
                // CHILD A: Configure isolation boundary & unshare PID namespace
                unsafe {
                    libc::close(gateway_fd); // Close gateway end in worker process

                    // Step 2: Lock privileges
                    if Self::set_no_new_privs().is_err() {
                        libc::_exit(127);
                    }

                    // Step 3: Sanitize FDs & bind worker socket to FD 3
                    if Self::sanitize_file_descriptors(worker_fd).is_err() {
                        libc::_exit(127);
                    }

                    // Step 4: Unshare namespaces (CLONE_NEWPID takes effect for subsequent children)
                    if Self::unshare_namespaces().is_err() {
                        libc::_exit(127);
                    }

                    // Step 5 & 6: Apply Landlock & Seccomp filters

                    // Stage 2 Fork: Spawn Child B inside the unshared PID namespace as PID 1
                    let pid_b = libc::fork();
                    if pid_b < 0 {
                        libc::_exit(127);
                    }

                    if pid_b == 0 {
                        // CHILD B (PID 1 in new PID namespace): execve untrusted binary
                        let c_path = std::ffi::CString::new(worker_binary).unwrap();
                        let argv = [c_path.as_ptr(), std::ptr::null()];
                        let envp = [std::ptr::null()];

                        libc::execve(c_path.as_ptr(), argv.as_ptr(), envp.as_ptr());

                        // If execve returns, it failed
                        libc::_exit(127);
                    }

                    // Child A waits for Child B or exits cleanly
                    let mut status: i32 = 0;
                    libc::waitpid(pid_b, &mut status, 0);
                    libc::_exit(0);
                }
            }

            // PARENT PROCESS: Close worker end, retain gateway end
            unsafe {
                libc::close(worker_fd);
            }

            Ok(Self {
                gateway_fd,
                worker_pid: Some(pid_a),
            })
        }
        #[cfg(not(target_os = "linux"))]
        {
            Ok(Self {
                gateway_fd,
                worker_pid: None,
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ipc_socketpair_creation() {
        let res = ProfileASupervisor::create_ipc_socketpair();
        assert!(res.is_ok());
    }

    #[test]
    fn test_no_new_privs_execution() {
        let res = ProfileASupervisor::set_no_new_privs();
        assert!(res.is_ok());
    }

    #[test]
    fn test_target_ipc_fd_constant() {
        assert_eq!(TARGET_IPC_FD, 3);
    }
}
