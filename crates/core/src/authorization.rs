/// Conservative ownership decision for one user service spanning graphical seats.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SessionCandidate {
    pub active: bool,
    pub locked: bool,
    pub remote: bool,
    pub wayland: bool,
    pub seat: String,
}
pub fn select_session(candidates: &[SessionCandidate]) -> (bool, bool) {
    let mut local = candidates.iter().filter(|session| {
        session.active && !session.remote && session.wayland && !session.seat.is_empty()
    });
    match (local.next(), local.next()) {
        (Some(session), None) => (true, session.locked),
        _ => (false, true),
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn candidate() -> SessionCandidate {
        SessionCandidate {
            active: true,
            locked: false,
            remote: false,
            wayland: true,
            seat: "seat0".into(),
        }
    }
    #[test]
    fn ambiguous_seats_deny_mutations() {
        assert_eq!(select_session(&[candidate()]), (true, false));
        assert_eq!(select_session(&[candidate(), candidate()]), (false, true));
        assert_eq!(select_session(&[]), (false, true));
    }
    #[test]
    fn remote_or_x11_sessions_do_not_own_workspace() {
        let mut remote = candidate();
        remote.remote = true;
        assert_eq!(select_session(&[remote]), (false, true));
        let mut locked = candidate();
        locked.locked = true;
        assert_eq!(select_session(&[locked]), (true, true));
    }
}
