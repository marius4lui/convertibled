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
        assert_eq!(de.value("specific device error"), "specific device error");
    }
}
