mod args;
#[cfg(target_os = "linux")]
mod client;
use args::{Args, Command, ConfigCommand};
use clap::Parser;
#[tokio::main]
async fn main() {
    let args = Args::parse();
    let result = match &args.command {
        Command::Config {
            command: ConfigCommand::Validate { path },
        } => std::fs::read_to_string(path)
            .map_err(|e| e.to_string())
            .and_then(|text| {
                convertibled_core::config::Config::parse(&text)
                    .map(|_| "Configuration valid (schema 1)".to_string())
            }),
        Command::Profiles => Ok("auto\nlaptop\ntablet\nstand (manual)\ntent (manual)".into()),
        _ => run(&args).await,
    };
    match result {
        Ok(text) => {
            if !text.is_empty() {
                println!("{text}")
            }
        }
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(3);
        }
    }
}
#[cfg(target_os = "linux")]
async fn run(args: &Args) -> Result<String, String> {
    client::run(args).await
}
#[cfg(not(target_os = "linux"))]
async fn run(_: &Args) -> Result<String, String> {
    Err("This command requires Linux D-Bus".into())
}
