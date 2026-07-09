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
    if content_width < 700.0 {
        145.0
    } else if content_width < 1100.0 {
        150.0
    } else {
        165.0
    }
}

pub fn metric_cards_per_row(content_width: f32, card_width: f32, item_spacing: f32) -> usize {
    if card_width <= 0.0 {
        return 1;
    }

    let columns = ((content_width + item_spacing) / (card_width + item_spacing)).floor() as usize;
    columns.max(1)
}

pub fn operation_log_height(expanded: bool) -> f32 {
    if expanded {
        170.0
    } else {
        42.0
    }
}

#[cfg(test)]
mod tests {
    use super::TwoPaneMode;
    use super::{
        dashboard_columns_for_width, dense_table_mode_for_width, metric_card_width,
        metric_cards_per_row, operation_log_height,
    };

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
        assert_eq!(metric_card_width(860.0), 150.0);
        assert_eq!(metric_card_width(1180.0), 165.0);
    }

    #[test]
    fn computes_metric_card_rows_without_partial_right_edge_cards() {
        assert_eq!(metric_cards_per_row(860.0, 150.0, 8.0), 5);
        assert_eq!(metric_cards_per_row(760.0, 150.0, 8.0), 4);
        assert_eq!(metric_cards_per_row(320.0, 145.0, 8.0), 2);
        assert_eq!(metric_cards_per_row(120.0, 145.0, 8.0), 1);
    }

    #[test]
    fn keeps_operation_log_compact_by_default_but_expandable() {
        assert_eq!(operation_log_height(false), 42.0);
        assert_eq!(operation_log_height(true), 170.0);
        assert!(operation_log_height(true) > operation_log_height(false));
    }
}
