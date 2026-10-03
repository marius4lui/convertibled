use crate::Posture;
use std::time::Duration;

/// Debounce monotonic samples; conflicting hardware immediately loses certainty.
pub struct Debouncer {
    stable: Posture,
    candidate: Posture,
    since: Duration,
    delay: Duration,
}
impl Debouncer {
    pub fn new(delay: Duration) -> Self {
        Self {
            stable: Posture::Unknown,
            candidate: Posture::Unknown,
            since: Duration::ZERO,
            delay,
        }
    }
    pub fn sample(&mut self, samples: &[bool], now: Duration) -> Posture {
        let next = match samples.first() {
            Some(first) if samples.iter().all(|value| value == first) => {
                if *first {
                    Posture::Folded
                } else {
                    Posture::Laptop
                }
            }
            _ => Posture::Unknown,
        };
        if next == Posture::Unknown {
            self.stable = next;
            self.candidate = next;
            self.since = now;
            return next;
        }
        if next != self.candidate {
            self.candidate = next;
            self.since = now;
        }
        if now.saturating_sub(self.since) >= self.delay {
            self.stable = next;
        }
        self.stable
    }
    pub fn invalidate(&mut self) {
        self.stable = Posture::Unknown;
        self.candidate = Posture::Unknown;
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn bounces_do_not_replace_stable_posture() {
        let mut d = Debouncer::new(Duration::from_millis(300));
        assert_eq!(d.sample(&[true], Duration::ZERO), Posture::Unknown);
        assert_eq!(
            d.sample(&[false], Duration::from_millis(100)),
            Posture::Unknown
        );
        assert_eq!(
            d.sample(&[true], Duration::from_millis(200)),
            Posture::Unknown
        );
        assert_eq!(
            d.sample(&[true], Duration::from_millis(500)),
            Posture::Folded
        );
        assert_eq!(
            d.sample(&[false], Duration::from_millis(550)),
            Posture::Folded
        );
    }
    #[test]
    fn conflicting_or_lost_devices_are_unknown() {
        let mut d = Debouncer::new(Duration::from_millis(50));
        d.sample(&[true], Duration::ZERO);
        d.sample(&[true], Duration::from_secs(1));
        assert_eq!(
            d.sample(&[true, false], Duration::from_secs(2)),
            Posture::Unknown
        );
        assert_eq!(d.sample(&[], Duration::from_secs(3)), Posture::Unknown);
    }
}
