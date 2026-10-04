use clap::{Parser, Subcommand};
use std::path::PathBuf;
#[derive(Parser)]
#[command(
    name = "convertiblectl",
    version,
    about = "Convertible status and supported controls"
)]
pub struct Args {
    #[arg(long, global = true)]
    pub json: bool,
    #[command(subcommand)]
    pub command: Command,
}
#[derive(Subcommand)]
pub enum Command {
    Status,
    Devices,
    Capabilities,
    Watch {
        #[arg(long)]
        count: Option<u32>,
    },
    Doctor {
        #[arg(long)]
        export: Option<PathBuf>,
    },
    Mode {
        profile: String,
    },
    RotationLock {
        #[arg(value_parser=["on","off"])]
        value: String,
    },
    Profiles,
    Config {
        #[command(subcommand)]
        command: ConfigCommand,
    },
    Reload,
    Update {
        #[arg(value_parser=["check","prepare","status","activate","rollback"])]
        action: String,
    },
}
#[derive(Subcommand)]
pub enum ConfigCommand {
    Validate { path: PathBuf },
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_json_and_bounded_watch() {
        let args =
            Args::try_parse_from(["convertiblectl", "watch", "--count", "2", "--json"]).unwrap();
        assert!(args.json);
        assert!(matches!(args.command, Command::Watch { count: Some(2) }));
    }
    #[test]
    fn rejects_arbitrary_update_commands() {
        assert!(Args::try_parse_from(["convertiblectl", "update", "shell"]).is_err());
    }
}
