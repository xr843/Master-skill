use std::ffi::OsString;
use std::fmt;

pub const DESKTOP_USAGE: &str = "Usage: master-skill-desktop [--baseline | --help]\n\n\
Options:\n  --baseline  Run the headless fidelity dry-run baseline\n  \
-h, --help  Print this help";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LaunchMode {
    Gui,
    Baseline,
    Help,
}

#[derive(Debug)]
pub struct LaunchArgsError {
    args: Vec<OsString>,
}

impl fmt::Display for LaunchArgsError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid arguments: {:?}", self.args)
    }
}

impl std::error::Error for LaunchArgsError {}

pub fn parse_launch_mode(
    args: impl IntoIterator<Item = OsString>,
) -> Result<LaunchMode, LaunchArgsError> {
    let args: Vec<OsString> = args.into_iter().collect();
    match args.as_slice() {
        [] => Ok(LaunchMode::Gui),
        [argument] if argument == "--baseline" => Ok(LaunchMode::Baseline),
        [argument] if argument == "--help" || argument == "-h" => Ok(LaunchMode::Help),
        _ => Err(LaunchArgsError { args }),
    }
}

#[cfg(test)]
mod tests {
    use super::{parse_launch_mode, LaunchMode};
    use std::ffi::OsString;

    fn args(values: &[&str]) -> Vec<OsString> {
        values.iter().map(OsString::from).collect()
    }

    #[test]
    fn parses_only_the_supported_launch_modes() {
        assert_eq!(parse_launch_mode(args(&[])).unwrap(), LaunchMode::Gui);
        assert_eq!(
            parse_launch_mode(args(&["--baseline"])).unwrap(),
            LaunchMode::Baseline
        );
        assert_eq!(
            parse_launch_mode(args(&["--help"])).unwrap(),
            LaunchMode::Help
        );
        assert_eq!(parse_launch_mode(args(&["-h"])).unwrap(), LaunchMode::Help);
        assert!(parse_launch_mode(args(&["--unknown"])).is_err());
        assert!(parse_launch_mode(args(&["--baseline", "extra"])).is_err());
    }
}
