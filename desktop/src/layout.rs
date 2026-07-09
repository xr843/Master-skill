#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TwoPaneMode {
    SingleColumn,
    TwoColumns,
}

pub fn dashboard_columns_for_width(width: f32) -> TwoPaneMode {
    if width >= 900.0 {
        TwoPaneMode::TwoColumns
    } else {
        TwoPaneMode::SingleColumn
    }
}

#[cfg(test)]
mod tests {
    use super::{dashboard_columns_for_width, TwoPaneMode};

    #[test]
    fn uses_single_column_for_narrow_content_widths() {
        assert_eq!(
            dashboard_columns_for_width(620.0),
            TwoPaneMode::SingleColumn
        );
    }

    #[test]
    fn uses_two_columns_for_wide_content_widths() {
        assert_eq!(dashboard_columns_for_width(980.0), TwoPaneMode::TwoColumns);
    }
}
