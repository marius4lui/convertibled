use gtk::gio;
use std::ffi::OsStr;

pub const HELPER: &str = "/opt/convertibled/current/installer/cli.py";

pub async fn helper(command: &str, value: Option<&str>) -> Result<serde_json::Value, String> {
    let mut args = Vec::new();
    if command != "status" {
        args.push("/usr/bin/pkexec");
    }
    args.extend([HELPER, command]);
    if let Some(value) = value {
        args.push(value);
    }
    let output = run(&args).await?;
    crate::model::parse_status(&output)
}

pub async fn run(args: &[&str]) -> Result<String, String> {
    let args: Vec<&OsStr> = args.iter().map(OsStr::new).collect();
    let process = gio::Subprocess::newv(
        &args,
        gio::SubprocessFlags::STDOUT_PIPE | gio::SubprocessFlags::STDERR_PIPE,
    )
    .map_err(|error| error.to_string())?;
    // IO is asynchronous. Privileged mutations have their own journal; closing
    // this window must not interrupt a critical activation or configuration write.
    let (output, error) = process
        .communicate_utf8_future(None)
        .await
        .map_err(|e| e.to_string())?;
    if !process.is_successful() {
        return Err(error
            .map(|v| v.to_string())
            .filter(|v| !v.trim().is_empty())
            .unwrap_or_else(|| "Operation failed or authorization was cancelled".into()));
    }
    let output = output.map(|v| v.to_string()).unwrap_or_default();
    if output.len() > 1024 * 1024 {
        return Err("Response exceeds supported size".into());
    }
    Ok(output)
}
