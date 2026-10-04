//! Small compile-time bilingual catalog; no network or downloaded translations.
#[derive(Clone, Copy)]
pub struct Strings {
    german: bool,
}

impl Strings {
    pub fn detect() -> Self {
        let locale = ["LC_ALL", "LC_MESSAGES", "LANG"]
            .iter()
            .filter_map(|name| std::env::var(name).ok())
            .find(|value| !value.is_empty())
            .unwrap_or_default();
        Self::for_locale(&locale)
    }

    pub fn for_locale(locale: &str) -> Self {
        Self {
            german: locale.split(['_', '-', '.']).next() == Some("de"),
        }
    }

    pub fn text(self, english: &'static str, german: &'static str) -> &'static str {
        if self.german { german } else { english }
    }

    pub fn profile(self, profile: &str) -> &str {
        match profile {
            "auto" => self.text("Automatic", "Automatisch"),
            "laptop" => self.text("Laptop", "Laptop"),
            "tablet" => self.text("Tablet", "Tablet"),
            "stand" => self.text("Stand", "Stand"),
            "tent" => self.text("Tent", "Zelt"),
            _ => self.text("Unknown", "Unbekannt"),
        }
    }

    pub fn value(self, value: &str) -> String {
        let translated = match value {
            "true" => self.text("Yes", "Ja"),
            "false" => self.text("No", "Nein"),
            "unknown" => self.text("Unknown", "Unbekannt"),
            "folded" => self.text("Folded", "Umgeklappt"),
            "auto" | "laptop" | "tablet" | "stand" | "tent" => self.profile(value),
            "applied" => self.text("Applied", "Angewendet"),
            "failed" => self.text("Failed", "Fehlgeschlagen"),
            "unavailable" => self.text("Unavailable", "Nicht verfügbar"),
            "unsupported" => self.text("Unsupported", "Nicht unterstützt"),
            "enabled" => self.text("Enabled", "Aktiviert"),
            "disabled" => self.text("Disabled", "Deaktiviert"),
            "unchanged" => self.text("Unchanged", "Unverändert"),
            "awaiting_shell" => self.text("Waiting for next login", "Wartet auf nächste Anmeldung"),
            "waiting_for_logout" | "waiting" => self.text(
                "Waiting for all graphical users to log out",
                "Wartet auf die Abmeldung aller grafischen Benutzer",
            ),
            "action_failed" => self.text(
                "Scheduled action failed — review details",
                "Geplante Aktion fehlgeschlagen — Details prüfen",
            ),
            "running" => self.text(
                "Applying scheduled action",
                "Geplante Aktion wird ausgeführt",
            ),
            "uninstall" => self.text("Remove convertibled", "convertibled entfernen"),
            "pending_intent" => {
                self.text("Waiting for desktop check", "Desktop-Prüfung ausstehend")
            }
            "verified" => self.text(
                "Enabled workspace reported healthy",
                "Aktivierter Workspace hat Bereitschaft bestätigt",
            ),
            "not_requested" => self.text(
                "Workspace not requested; services checked",
                "Workspace nicht angefordert; Dienste geprüft",
            ),
            "activate" => self.text(
                "Install prepared version",
                "Vorbereitete Version installieren",
            ),
            "rollback" => self.text(
                "Restore previous version",
                "Vorherige Version wiederherstellen",
            ),
            "recover" => self.text(
                "Recover interrupted transaction",
                "Unterbrochene Transaktion wiederherstellen",
            ),
            "complete" => self.text("Complete", "Abgeschlossen"),
            "rolled_back" => self.text(
                "Previous version restored",
                "Vorherige Version wiederhergestellt",
            ),
            "idle" => self.text("Idle", "Bereit"),
            "not_installed" => self.text("Not installed", "Nicht installiert"),
            _ => value,
        };
        translated.to_owned()
    }

    pub fn error(self, detail: &str) -> String {
        let lower = detail.to_lowercase();
        if lower.contains("without an owner")
            || lower.contains("serviceunknown")
            || lower.contains("do_not_auto_start")
            || lower.contains("namehasnoowner")
        {
            return self.text("The session service is unavailable. Sign in again after installation.",
                "Der Sitzungsdienst ist nicht erreichbar. Melde dich nach der Installation erneut an.").into();
        }
        if lower.contains("failed to execute child process")
            || lower.contains("extension schema unavailable")
        {
            return self.text("This component is not installed. Complete installation and reopen settings.",
                "Diese Komponente ist nicht installiert. Schließe die Installation ab und öffne die Einstellungen erneut.").into();
        }
        if lower.contains("accessdenied") {
            return self
                .text(
                    "This action requires your active, unlocked local session.",
                    "Diese Aktion benötigt deine aktive, entsperrte lokale Sitzung.",
                )
                .into();
        }
        detail.into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn locale_variants_and_fallback() {
        for locale in ["de", "de_DE.UTF-8", "de-AT"] {
            assert_eq!(Strings::for_locale(locale).profile("auto"), "Automatisch");
        }
        for locale in ["", "C", "en_US.UTF-8", "fr_FR", "den"] {
            assert_eq!(Strings::for_locale(locale).profile("tent"), "Tent");
        }
    }

    #[test]
    fn translates_states_without_altering_error_details() {
        let de = Strings::for_locale("de_DE");
        assert_eq!(de.value("failed"), "Fehlgeschlagen");
        assert_eq!(de.value("true"), "Ja");
        assert_eq!(de.value("activate"), "Vorbereitete Version installieren");
        assert_eq!(de.value("pending_intent"), "Desktop-Prüfung ausstehend");
        assert!(de.value("not_requested").contains("nicht angefordert"));
        assert_eq!(de.value("specific device error"), "specific device error");
    }

    #[test]
    fn explains_service_failures_without_internal_proxy_flags() {
        let de = Strings::for_locale("de");
        let message = de.error("proxy without an owner: G_DBUS_PROXY_FLAGS_DO_NOT_AUTO_START");
        assert!(message.contains("Sitzungsdienst"));
        assert!(!message.contains("G_DBUS"));
        assert_eq!(
            de.error("Specific recovery failure"),
            "Specific recovery failure"
        );
    }
}
