/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Bridge to the bundled `sml2c` (BSML2 / SCRUM-446). Port of `sml2cBridge.ts`:
 * resolve the binary, run it with an `--emit-*` flag over a `.sysml`, and
 * capture stdout / stderr / exit code (via temp-file redirection so both the
 * emitted artifact and the diagnostics are recovered).
 */

#include "sml2c_bridge.hh"

#include <atomic>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "BLI_fileops.hh"
#include "BLI_path_utils.hh"

#include "BKE_appdir.hh"

#ifdef WIN32
#  include <windows.h>
#else
#  include <fcntl.h>
#  include <spawn.h>
#  include <sys/wait.h>
#  include <unistd.h>
extern char **environ;
#endif

namespace blender::nodes::sysml {

#ifdef WIN32
#  define SML2C_EXE_NAME "sml2c.exe"
#else
#  define SML2C_EXE_NAME "sml2c"
#endif

std::string sml2c_binary_path()
{
  if (const char *env = std::getenv("SML2C")) {
    if (env[0] != '\0' && BLI_exists(env)) {
      return env;
    }
  }
  char path[1024];
  BLI_path_join(path, sizeof(path), BKE_appdir_program_dir(), SML2C_EXE_NAME);
  if (BLI_exists(path)) {
    return path;
  }
  return "";
}

std::string sml2c_stdlib_path()
{
  if (const char *env = std::getenv("SML2C_STDLIB")) {
    if (env[0] != '\0' && BLI_exists(env)) {
      return env;
    }
  }
  char path[1024];
  BLI_path_join(path, sizeof(path), BKE_appdir_program_dir(), "sysml-stdlib");
  if (BLI_exists(path)) {
    return path;
  }
  return "";
}

static std::string read_text_file(const char *path)
{
  std::ifstream f(path, std::ios::binary);
  std::ostringstream ss;
  ss << f.rdbuf();
  return ss.str();
}

Sml2cResult sml2c_run(StringRefNull emit_flag, StringRefNull sysml_path)
{
  Sml2cResult result;

  if (!BLI_exists(sysml_path.c_str())) {
    result.error = std::string("File not found: ") + sysml_path.c_str();
    return result;
  }
  const std::string bin = sml2c_binary_path();
  if (bin.empty()) {
    result.error =
        "sml2c binary not found. Set $SML2C, or install sml2c next to the Blender executable.";
    return result;
  }
  /* Resolve library-defined types (SpatialItem, shapes) against the bundled
   * minimal standard library when present. */
  const std::string stdlib = sml2c_stdlib_path();

  /* Unique temp files to capture stdout/stderr (atomic counter guards against
   * overlapping invocations sharing a name). */
  static std::atomic<unsigned> counter{0};
  const unsigned id = counter.fetch_add(1);
  const std::string out_name = "sml2c_out_" + std::to_string(id) + ".tmp";
  const std::string err_name = "sml2c_err_" + std::to_string(id) + ".tmp";
  char out_path[1024], err_path[1024];
  BLI_path_join(out_path, sizeof(out_path), BKE_tempdir_base(), out_name.c_str());
  BLI_path_join(err_path, sizeof(err_path), BKE_tempdir_base(), err_name.c_str());

#ifdef WIN32
  SECURITY_ATTRIBUTES sa{};
  sa.nLength = sizeof(sa);
  sa.bInheritHandle = TRUE;
  HANDLE h_out = CreateFileA(
      out_path, GENERIC_WRITE, FILE_SHARE_READ, &sa, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
  HANDLE h_err = CreateFileA(
      err_path, GENERIC_WRITE, FILE_SHARE_READ, &sa, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (h_out == INVALID_HANDLE_VALUE || h_err == INVALID_HANDLE_VALUE) {
    result.error = "failed to create temp capture files";
    return result;
  }
  STARTUPINFOA si{};
  si.cb = sizeof(si);
  si.dwFlags = STARTF_USESTDHANDLES;
  si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
  si.hStdOutput = h_out;
  si.hStdError = h_err;

  std::string cmd = "\"" + bin + "\"";
  if (!stdlib.empty()) {
    cmd += " --stdlib-path \"" + stdlib + "\"";
  }
  cmd += " " + std::string(emit_flag.c_str()) + " \"" + std::string(sysml_path.c_str()) + "\"";
  std::vector<char> cmd_buf(cmd.begin(), cmd.end());
  cmd_buf.push_back('\0');

  PROCESS_INFORMATION pi{};
  const BOOL launched = CreateProcessA(
      bin.c_str(), cmd_buf.data(), nullptr, nullptr, TRUE, 0, nullptr, nullptr, &si, &pi);
  CloseHandle(h_out);
  CloseHandle(h_err);
  if (!launched) {
    result.error = "failed to launch sml2c";
    BLI_delete(out_path, false, false);
    BLI_delete(err_path, false, false);
    return result;
  }
  WaitForSingleObject(pi.hProcess, INFINITE);
  DWORD code = 0;
  GetExitCodeProcess(pi.hProcess, &code);
  CloseHandle(pi.hProcess);
  CloseHandle(pi.hThread);
  result.exit_code = int(code);
#else
  const int out_fd = open(out_path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
  const int err_fd = open(err_path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
  if (out_fd < 0 || err_fd < 0) {
    result.error = "failed to create temp capture files";
    return result;
  }
  posix_spawn_file_actions_t actions;
  posix_spawn_file_actions_init(&actions);
  posix_spawn_file_actions_adddup2(&actions, out_fd, STDOUT_FILENO);
  posix_spawn_file_actions_adddup2(&actions, err_fd, STDERR_FILENO);

  const std::string flag_s = emit_flag.c_str();
  const std::string path_s = sysml_path.c_str();
  std::vector<char *> argv;
  argv.push_back(const_cast<char *>(bin.c_str()));
  if (!stdlib.empty()) {
    argv.push_back(const_cast<char *>("--stdlib-path"));
    argv.push_back(const_cast<char *>(stdlib.c_str()));
  }
  argv.push_back(const_cast<char *>(flag_s.c_str()));
  argv.push_back(const_cast<char *>(path_s.c_str()));
  argv.push_back(nullptr);
  pid_t pid;
  const int rc = posix_spawn(&pid, bin.c_str(), &actions, nullptr, argv.data(), environ);
  close(out_fd);
  close(err_fd);
  posix_spawn_file_actions_destroy(&actions);
  if (rc != 0) {
    result.error = "failed to launch sml2c";
    BLI_delete(out_path, false, false);
    BLI_delete(err_path, false, false);
    return result;
  }
  int status = 0;
  waitpid(pid, &status, 0);
  result.exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
#endif

  result.output = read_text_file(out_path);
  result.diagnostics = read_text_file(err_path);
  BLI_delete(out_path, false, false);
  BLI_delete(err_path, false, false);

  result.ok = (result.exit_code == 0);
  if (!result.ok && result.error.empty()) {
    result.error = "sml2c exited with code " + std::to_string(result.exit_code);
  }
  return result;
}

}  // namespace blender::nodes::sysml
