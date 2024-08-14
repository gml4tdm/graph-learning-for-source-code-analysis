use ratatui::layout::{Constraint, Layout, Rect};


#[allow(unused)]
pub fn popup(area: Rect,
             width: Constraint, 
             height: Constraint) -> Rect {
    floating_box(
        area,
        [
            Constraint::Fill(1),
            width,
            Constraint::Fill(1)
        ],
        [
            Constraint::Fill(1),
            height,
            Constraint::Fill(1)
        ]
    )
}


#[allow(unused)]
pub fn floating_box(area: Rect,
                    horizontal_spec: [Constraint; 3], 
                    vertical_spec: [Constraint; 3]) -> Rect {
    let vertical_chunks = Layout::default()
        .direction(ratatui::layout::Direction::Vertical)
        .constraints(vertical_spec)
        .split(area);
    let horizontal_chunks = Layout::default()
        .direction(ratatui::layout::Direction::Horizontal)
        .constraints(horizontal_spec)
        .split(vertical_chunks[1]);
    horizontal_chunks[1]
}
