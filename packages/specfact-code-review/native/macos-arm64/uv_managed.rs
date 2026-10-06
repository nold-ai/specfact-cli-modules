//! Private broker transport for the pinned Darwin uv distribution.
//! No process is created here; program paths select only a private Python prefix.

use std::collections::BTreeMap;
use std::fs::File;
use std::io::{self, Read, Write};
use std::os::fd::{BorrowedFd, FromRawFd, IntoRawFd};
use std::os::unix::fs::FileTypeExt;
use std::os::unix::process::ExitStatusExt;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitStatus, Output};
use std::sync::Mutex;
use std::time::Duration;

const MAGIC: u32 = 0x53464d31;
const PAYLOAD: usize = 4096;
const OUTPUT: usize = 4 << 20;
static CHANNEL: Mutex<()> = Mutex::new(());

fn unsupported(reason: &str) -> io::Error {
    io::Error::new(io::ErrorKind::Unsupported, format!("project_native_managed_process_incomplete:{reason}"))
}

pub fn active() -> bool {
    std::env::var("SPECFACT_MANAGED_UV").is_ok_and(|value| value == "1")
}

fn pipe(descriptor: i32) -> io::Result<File> {
    // Duplicate, never take ownership of the inherited endpoint.
    let owned = unsafe { BorrowedFd::borrow_raw(descriptor) }.try_clone_to_owned()?;
    let file = unsafe { File::from_raw_fd(owned.into_raw_fd()) };
    if !file.metadata()?.file_type().is_fifo() {
        return Err(unsupported("worker channel is not a pipe"));
    }
    Ok(file)
}

fn exchange(opcode: u16, handle: u32, payload: &[u8]) -> io::Result<(u32, i32, Vec<u8>)> {
    if payload.len() > PAYLOAD || !(1..=8).contains(&opcode) {
        return Err(unsupported("request exceeds bounds"));
    }
    let _guard = CHANNEL.lock().map_err(|_| unsupported("worker channel lock poisoned"))?;
    let mut request = pipe(5)?;
    let mut reply = pipe(6)?;
    request.write_all(&MAGIC.to_le_bytes())?;
    request.write_all(&1u16.to_le_bytes())?;
    request.write_all(&opcode.to_le_bytes())?;
    request.write_all(&handle.to_le_bytes())?;
    request.write_all(&(payload.len() as u32).to_le_bytes())?;
    request.write_all(payload)?;
    let mut header = [0u8; 20];
    reply.read_exact(&mut header)?;
    let u32_at = |index| u32::from_le_bytes(header[index..index + 4].try_into().unwrap());
    let returned = u32_at(8);
    let length = u32_at(16) as usize;
    if u32_at(0) != MAGIC || header[4..6] != 1u16.to_le_bytes()
        || (opcode != 1 && returned != handle) {
        return Err(unsupported("invalid broker response"));
    }
    if header[6..8] != 0u16.to_le_bytes() {
        return Err(unsupported(&format!("broker rejected operation {opcode}: errno={length}")));
    }
    if length > PAYLOAD {
        return Err(unsupported("reply exceeds bounds"));
    }
    let mut data = vec![0u8; length];
    reply.read_exact(&mut data)?;
    Ok((returned, i32::from_le_bytes(header[12..16].try_into().unwrap()), data))
}

fn xml(value: &str) -> io::Result<String> {
    if value.len() >= PAYLOAD || value.chars().any(|c| c < ' ' && !matches!(c, '\n' | '\r' | '\t')) {
        return Err(unsupported("invalid argument string"));
    }
    Ok(value.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;"))
}

fn text(value: &str) -> io::Result<String> {
    Ok(format!("<string>{}</string>", xml(value)?))
}

#[cfg(target_os = "macos")]
mod property_list {
    use super::{unsupported, PAYLOAD};
    use std::ffi::c_void;
    use std::io;
    use std::ptr;

    #[link(name = "CoreFoundation", kind = "framework")]
    unsafe extern "C" {
        fn CFDataCreate(allocator: *const c_void, bytes: *const u8, length: isize) -> *const c_void;
        fn CFPropertyListCreateWithData(allocator: *const c_void, data: *const c_void, options: usize,
            format: *mut isize, error: *mut *const c_void) -> *const c_void;
        fn CFPropertyListCreateData(allocator: *const c_void, document: *const c_void, format: isize,
            options: usize, error: *mut *const c_void) -> *const c_void;
        fn CFDataGetLength(data: *const c_void) -> isize;
        fn CFDataGetBytePtr(data: *const c_void) -> *const u8;
        fn CFRelease(value: *const c_void);
    }

    struct Owned(*const c_void);
    impl Owned {
        fn checked(value: *const c_void) -> io::Result<Self> {
            if value.is_null() { return Err(unsupported("invalid launch property list")); }
            Ok(Self(value))
        }
    }
    impl Drop for Owned {
        fn drop(&mut self) { unsafe { CFRelease(self.0); } }
    }

    pub fn encode(xml: &[u8]) -> io::Result<Vec<u8>> {
        // CoreFoundation is already the broker's property-list parser. Only
        // serialization changes; no execution selector or grant is rewritten.
        unsafe {
            let input = Owned::checked(CFDataCreate(ptr::null(), xml.as_ptr(), xml.len() as isize))?;
            let document = Owned::checked(CFPropertyListCreateWithData(ptr::null(), input.0, 0,
                ptr::null_mut(), ptr::null_mut()))?;
            let output = Owned::checked(CFPropertyListCreateData(ptr::null(), document.0, 200, 0, ptr::null_mut()))?;
            let length = CFDataGetLength(output.0);
            if length <= 0 || length as usize > PAYLOAD { return Err(unsupported("request exceeds bounds")); }
            let bytes = CFDataGetBytePtr(output.0);
            if bytes.is_null() { return Err(unsupported("invalid launch property list")); }
            Ok(std::slice::from_raw_parts(bytes, length as usize).to_vec())
        }
    }
}

#[cfg(not(target_os = "macos"))]
mod property_list {
    pub fn encode(_xml: &[u8]) -> std::io::Result<Vec<u8>> {
        Err(super::unsupported("managed uv requires macOS"))
    }
}

fn roots() -> io::Result<Vec<(&'static str, PathBuf)>> {
    ["project", "output", "temporary"].into_iter().map(|name| {
        let key = format!("SPECFACT_MANAGED_{}", name.to_uppercase());
        let path = PathBuf::from(std::env::var(key).map_err(|_| unsupported("worker roots missing"))?);
        if path.canonicalize()? != path || !path.is_dir() {
            return Err(unsupported("worker root is not canonical"));
        }
        Ok((name, path))
    }).collect()
}

fn private(path: &Path, roots: &[(&str, PathBuf)]) -> bool {
    path.is_absolute() && path.canonicalize().is_ok_and(|value| value == path)
        && roots.iter().any(|(_, root)| path.starts_with(root))
}

fn prefix(program: &Path, python: &Path, roots: &[(&str, PathBuf)]) -> io::Result<(String, String)> {
    if program == python {
        return Ok((String::new(), String::new()));
    }
    let alias = program.file_name().and_then(|v| v.to_str()).ok_or_else(|| unsupported("unknown Python alias"))?;
    if !matches!(alias, "python" | "python3" | "python3.11" | "python3.12" | "python3.13") {
        return Err(unsupported("unknown executable identity"));
    }
    let bin = program.parent().ok_or_else(|| unsupported("invalid Python alias"))?;
    let prefix = bin.parent().ok_or_else(|| unsupported("invalid Python prefix"))?;
    let config = prefix.join("pyvenv.cfg");
    if bin.file_name().is_none_or(|value| value != "bin") || !private(prefix, roots)
        || config.is_symlink() || config.metadata()?.len() > 16384
        || !std::fs::read_to_string(config)?.lines().any(|line| {
            line.split_once('=').is_some_and(|(name, value)|
                name.trim().eq_ignore_ascii_case("include-system-site-packages")
                    && value.trim().eq_ignore_ascii_case("false"))
        }) {
        return Err(unsupported("private Python environment is not admitted"));
    }
    // uv can copy an interpreter instead of making an alias. Its bytes must
    // match the fixed image; the broker still executes only that fixed image.
    if program.canonicalize()? != python.canonicalize()?
        && (program.metadata()?.len() > 16 << 20 || std::fs::read(program)? != std::fs::read(python)?) {
        return Err(unsupported("substituted Python alias"));
    }
    Ok((prefix.to_string_lossy().into_owned(), alias.into()))
}

fn document(command: &Command) -> io::Result<Vec<u8>> {
    let roots = roots()?;
    let capsule = PathBuf::from(std::env::var("SPECFACT_MANAGED_CAPSULE").map_err(|_| unsupported("capsule identity missing"))?);
    let python = capsule.join("python/bin/python3");
    let program = PathBuf::from(command.get_program());
    let (prefix, alias) = prefix(&program, &python, &roots)?;
    let cwd = command.get_current_dir().map(Path::to_path_buf).unwrap_or(std::env::current_dir()?);
    if !private(&cwd, &roots) || !cwd.is_dir() {
        return Err(unsupported("working directory exceeds inherited grants"));
    }
    let (label, root) = roots.iter().find(|(_, root)| cwd.starts_with(root)).unwrap();
    let relative = cwd.strip_prefix(root).unwrap();
    let cwd_label = if relative.as_os_str().is_empty() { label.to_string() }
        else { format!("{label}/{}", relative.to_string_lossy()) };
    let args = command.get_args().map(|value| value.to_str().ok_or_else(|| unsupported("non-UTF8 arguments")))
        .collect::<io::Result<Vec<_>>>()?;
    if args.is_empty() || args.len() > 128 {
        return Err(unsupported("argument bounds exceeded"));
    }
    let mut environment: BTreeMap<String, String> = std::env::vars().collect();
    for (key, value) in command.get_envs() {
        let key = key.to_str().ok_or_else(|| unsupported("non-UTF8 environment"))?;
        if let Some(value) = value {
            environment.insert(key.into(), value.to_str().ok_or_else(|| unsupported("non-UTF8 environment"))?.into());
        } else {
            environment.remove(key);
        }
    }
    environment.retain(|key, value| !key.starts_with("DYLD_") && !key.starts_with("LD_")
        && (!key.starts_with("PYTHON") || key == "PYTHONUTF8" && value == "1")
        && !matches!(key.as_str(), "PATH" | "HOME" | "TMPDIR")
        && !key.contains("TOKEN") && !key.contains("PASSWORD") && !key.contains("API_KEY"));
    if environment.len() > 128 {
        return Err(unsupported("environment bounds exceeded"));
    }
    let paths = if prefix.is_empty() { vec![] } else {
        ["3.11", "3.12", "3.13"].into_iter().map(|version| Path::new(&prefix).join(format!("lib/python{version}/site-packages")))
            .filter(|path| path.is_dir() && private(path, &roots)).collect::<Vec<_>>()
    };
    let mut body = String::from("<plist version=\"1.0\"><dict><key>program</key><string>python</string><key>argv</key><array>");
    for arg in args { body.push_str(&text(arg)?); }
    body.push_str("</array><key>cwd</key>"); body.push_str(&text(&cwd_label)?);
    body.push_str("<key>environment</key><dict>");
    for (key, value) in environment {
        body.push_str(&format!("<key>{}</key>{}", xml(&key)?, text(&value)?));
    }
    body.push_str("</dict><key>stdin_pipe</key><false/><key>merge_stderr</key><false/><key>python_paths</key><array>");
    for path in paths { body.push_str(&text(&path.to_string_lossy())?); }
    body.push_str("</array><key>python_prefix</key>"); body.push_str(&text(&prefix)?);
    body.push_str("<key>python_alias</key>"); body.push_str(&text(&alias)?);
    body.push_str("</dict></plist>");
    property_list::encode(body.as_bytes())
}

pub fn output(command: &Command) -> io::Result<Output> {
    let request = document(command)?;
    let (handle, status, _) = exchange(1, 0, &request)?;
    if handle == 0 || status != -1 { return Err(unsupported("invalid launch acknowledgment")); }
    let mut stdout = Vec::new();
    let mut stderr = Vec::new();
    let result = (|| {
        loop {
            let (_, status, _) = exchange(2, handle, &[])?;
            let (_, _, out) = exchange(4, handle, &4096u32.to_le_bytes())?;
            let (_, _, err) = exchange(5, handle, &4096u32.to_le_bytes())?;
            let empty = out.is_empty() && err.is_empty();
            stdout.extend(out); stderr.extend(err);
            if stdout.len() + stderr.len() > OUTPUT { return Err(unsupported("output exceeds bounds")); }
            if status != -1 && empty {
                exchange(8, handle, &[])?;
                return Ok(Output { status: ExitStatus::from_raw(status), stdout, stderr });
            }
            if empty { std::thread::sleep(Duration::from_millis(5)); }
        }
    })();
    if result.is_err() {
        // An owned handle, never a host PID. Parent failure also kills children.
        let _ = exchange(3, handle, &9u32.to_le_bytes());
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn arguments_remain_literal_xml_data() {
        assert_eq!(text("print('<x>&')").unwrap(), "<string>print('&lt;x&gt;&amp;')</string>");
        assert!(text("bad\0argument").is_err());
    }
    #[cfg(target_os = "macos")]
    #[test]
    fn managed_python_launch_retains_large_xml_fields_in_fixed_frame() {
        let capsule = PathBuf::from(std::env::var("SPECFACT_MANAGED_CAPSULE").unwrap());
        let mut command = Command::new(capsule.join("python/bin/python3"));
        command.args(["-c", &format!("print({:?})", "<literal>&".repeat(70))]);
        command.current_dir(std::env::var("SPECFACT_MANAGED_PROJECT").unwrap());
        for index in 0..30 {
            command.env(format!("BUILD_SETTING_{index}"), "literal<&>".repeat(10));
        }
        let payload = document(&command).unwrap();
        assert!(payload.len() <= PAYLOAD);
        assert!(payload.starts_with(b"bplist00"));
        println!("REQUEST={}", payload.iter().map(|value| format!("{value:02x}")).collect::<String>());
        command.env("OVERSIZED_STRING", "x".repeat(PAYLOAD));
        assert!(document(&command).is_err());
        command.env_remove("OVERSIZED_STRING");
        for index in 0..30 {
            command.env(format!("BUILD_SETTING_{index}"), format!("{index}:{}", "distinct large value".repeat(100)));
        }
        assert!(document(&command).is_err());
    }
    #[test]
    fn requests_are_bounded_before_channel_use() {
        assert!(exchange(0, 0, &[]).is_err());
        assert!(exchange(1, 0, &vec![0; PAYLOAD + 1]).is_err());
    }
}
