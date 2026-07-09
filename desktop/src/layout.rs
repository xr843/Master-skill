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

pub fn dense_table_mode_for_width(width: f32) -> TwoPaneMode {
    if width >= 1500.0 {
        TwoPaneMode::TwoColumns
    } else {
        TwoPaneMode::SingleColumn
    }
}

pub fn metric_card_width(content_width: f32) -> f32 {
    if content_width < 760.0 {
        145.0
    } else {
        165.0
    }
}

#[cfg(test)]
mod tests {
    use super::TwoPaneMode;
    use super::{dashboard_columns_for_width, dense_table_mode_for_width, metric_card_width};

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

    #[test]
    fn keeps_dense_tables_stacked_until_extra_wide_content_widths() {
        assert_eq!(
            dense_table_mode_for_width(1200.0),
            TwoPaneMode::SingleColumn
        );
        assert_eq!(
            dense_table_mode_for_width(1499.0),
            TwoPaneMode::SingleColumn
        );
        assert_eq!(dense_table_mode_for_width(1500.0), TwoPaneMode::TwoColumns);
    }

    #[test]
    fn uses_stable_metric_card_widths() {
        assert_eq!(metric_card_width(620.0), 145.0);
        assert_eq!(metric_card_width(980.0), 165.0);
    }
}
