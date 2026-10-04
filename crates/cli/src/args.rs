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
        #[arg(long,value_parser=clap::value_parser!(u32).range(1..))]
        count: Option<u32>,
    },
    Doctor {
        #[arg(long)]
        export: Option<PathBuf>,
    },
    Mode {
        #[arg(value_parser=["auto","laptop","tablet","stand","tent"])]
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
        #[command(subcommand)]
        command: UpdateCommand,
    },
}
#[derive(Subcommand)]
pub enum ConfigCommand {
    Validate { path: PathBuf },
    Show,
    Save { path: PathBuf },
}
#[derive(Subcommand)]
pub enum UpdateCommand {
    Check,
    Prepare,
    Status,
    Activate,
    /// Queue recovery after all graphical users log out.
    #[command(alias = "request-recover")]
    Recover,
    /// Queue the retained previous version after graphical logout.
    #[command(alias = "request-rollback")]
    Rollback,
    /// Queue removal after graphical logout, retaining configuration and data.
    #[command(alias = "request-uninstall")]
    Uninstall,
    /// Cancel waiting or failed maintenance; never interrupt a running switch.
    CancelPending,
    Automatic {
        #[arg(value_parser=["on","off"])]
        value: String,
    },
    Channel {
        #[arg(value_parser=["stable","preview"])]
        value: String,
    },
}
impl UpdateCommand {
    pub fn arguments(&self) -> Vec<&str> {
        match self {
            Self::Check => vec!["check"],
            Self::Prepare => vec!["prepare"],
            Self::Status => vec!["status"],
            Self::Activate => vec!["activate"],
            Self::Recover => vec!["request-recover"],
            Self::Rollback => vec!["request-rollback"],
            Self::Uninstall => vec!["request-uninstall"],
            Self::CancelPending => vec!["cancel-pending"],
            Self::Automatic { value } => vec!["automatic", value],
            Self::Channel { value } => vec!["channel", value],
        }
    }
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
    #[test]
    fn maintenance_queues_only_fixed_verbs_without_arguments() {
        for (verb, expected) in [
            ("recover", "request-recover"),
            ("request-recover", "request-recover"),
            ("rollback", "request-rollback"),
            ("request-rollback", "request-rollback"),
            ("uninstall", "request-uninstall"),
            ("request-uninstall", "request-uninstall"),
            ("cancel-pending", "cancel-pending"),
        ] {
            let args = Args::try_parse_from(["convertiblectl", "update", verb]).unwrap();
            let Command::Update { command } = args.command else {
                panic!("Expected update")
            };
            assert_eq!(command.arguments(), [expected]);
            assert!(
                Args::try_parse_from(["convertiblectl", "update", verb, "/tmp/other"]).is_err()
            );
        }
    }
    #[test]
    fn rejects_zero_watch_and_invalid_profiles() {
        assert!(Args::try_parse_from(["convertiblectl", "watch", "--count", "0"]).is_err());
        assert!(Args::try_parse_from(["convertiblectl", "mode", "arbitrary"]).is_err());
    }
    #[test]
    fn updater_preferences_are_fixed_argument_arrays() {
        let parsed =
            Args::try_parse_from(["convertiblectl", "update", "channel", "preview"]).unwrap();
        let Command::Update { command } = parsed.command else {
            panic!("Expected update")
        };
        assert_eq!(command.arguments(), ["channel", "preview"]);
        assert!(Args::try_parse_from(["convertiblectl", "update", "automatic", "maybe"]).is_err());
    }
}
