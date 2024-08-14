use ratatui::buffer::Buffer;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::prelude::{Color, Line, Span, StatefulWidget, Style, Stylize, Widget};
use ratatui::symbols::border;
use ratatui::widgets::{Block, Paragraph, Row, StatefulWidgetRef, Table};
use ratatui::widgets::block::{Position, Title};

use crate::widgets::text_input::TextInput;

use super::widget::FileDialogType;
use super::state::FileExplorerState;
use super::state::FileType;


pub(super) struct FileExplorerRenderer<'a> {
    outer_block: (Rect, Block<'a>),
    table: (Rect, Table<'a>),
    status: (Rect, Paragraph<'a>),
    input: Option<((Rect, Block<'a>), (Rect, TextInput))>,
    cursor: Option<(u16, u16)>,
}

impl<'a> FileExplorerRenderer<'a> {
    
    pub(super) fn new(area: Rect, 
                      file_dialog_type: FileDialogType, 
                      state: &FileExplorerState) -> Self 
    {
        let block = Self::draw_main_border(file_dialog_type);
        let inner = block.inner(area);
        let chunks = Layout::default()
            .direction(Direction::Vertical)
            .constraints([
                Constraint::Max(1),
                Constraint::Min(1)
            ])
            .split(inner);
        let status = Self::draw_status(state);
        let table = Self::draw_file_list( file_dialog_type, state);
        let (cursor, input) = if let Some(ref inner_state) = state.filename_input_state {
            let input = Self::draw_name_popup(area);
            let cursor = input.1.1.cursor(input.1.0, inner_state);
            (Some(cursor), Some(input))
        } else {
            (None, None)
        };
        Self {
            outer_block: (area, block),
            status: (chunks[0], status),
            table: (chunks[1], table),
            input,
            cursor
        }
    }
    
    pub(super) fn cursor(&self) -> Option<(u16, u16)> {
        self.cursor
    }
    
    fn draw_main_border(file_dialog_type: FileDialogType) -> Block<'a> {
        let instructions = Title::from(
            Line::from(
                vec![
                    " File Up/Down ".into(),
                    "<\u{2191}/\u{2193}>".blue().bold(),
                    " Directory Up/Down ".into(),
                    "<\u{2190}/\u{2192}>".blue().bold(),
                    if file_dialog_type == FileDialogType::AskSaveAsFilename {
                        " Enter Filename ".into()
                    } else {
                        "".into()
                    },
                    if file_dialog_type == FileDialogType::AskSaveAsFilename {
                        "<n>".blue().bold()
                    } else {
                        "".into()
                    },
                    " Confirm ".into(),
                    "<Enter>".blue().bold(),
                    " Cancel ".into(),
                    "<Esc>".blue().bold(),
                ]
            )
        );
        Block::bordered()
            .title(Title::from("Select a File".bold()).alignment(Alignment::Center))
            .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
            .border_set(border::THICK)
    }
    
    fn draw_status(state: &FileExplorerState) -> Paragraph<'a> {
        let dir_name = state.directory
            .clone()
            .into_os_string()
            .into_string()
            .expect("Failed to convert path name");
        let text = format!("Current directory: {}", dir_name);
        let error = state.io_error.as_ref().cloned().unwrap_or_default();
        let line = Line::from(vec![
            Span::styled(text, Style::new().fg(Color::Green).bold()),
            Span::styled(error, Style::new().fg(Color::White).bg(Color::Red).bold())
        ]);
        Paragraph::new(line).alignment(Alignment::Left)
    }
    
    fn draw_file_list(file_dialog_type: FileDialogType, 
                      state: &FileExplorerState) -> Table<'a> 
    {
        let table = Table::new(
            state.files.iter()
                .filter(
                    |info| (!info.file_type.is_file()) || file_dialog_type.show_filenames()
                )
                .map(|info| {
                    let style = match info.file_type {
                        FileType::File => Style::new().light_red(),
                        FileType::Directory => Style::new().cyan(),
                        FileType::FileSymlink => Style::new().light_magenta(),
                        FileType::DirectorySymlink => Style::new().light_blue(),
                    };
                    Row::new(vec![
                        Span::raw(if info.file_type.is_symlink() { "\u{1F517}" } else { "" }),
                        Span::raw(if info.file_type.is_dir() { "\u{1F4C1}" } else { "\u{1F4C4}" }),
                        Span::styled(info.name.clone(), style)
                    ])
                }),
            [
                Constraint::Length(2),
                Constraint::Length(2),
                Constraint::Min(1)
            ]
        );
        table.highlight_style(Style::new().bg(Color::LightYellow))
    }
    
    fn draw_name_popup(area: Rect) -> ((Rect, Block<'a>), (Rect, TextInput)) {
        let area = crate::widgets::util::popup::popup(
            area, Constraint::Percentage(40), Constraint::Length(3)
        );
        let instructions = Title::from(
            Line::from(
                vec![
                    " Cancel ".into(),
                    "Esc".blue().bold(),
                ]
            )
        );
        let block = Block::bordered()
            .title(Title::from("Enter a Filename".bold()).alignment(Alignment::Center))
            .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
            .border_set(border::THICK);
        let input_field = TextInput::new();
        let inner = block.inner(area);
        ((area, block), (inner, input_field))
    }
    
    pub(super) fn render(self, buf: &mut Buffer, state: &mut FileExplorerState) {
        let (area, block) = self.outer_block;
        block.render(area, buf);
        let (area, table) = self.table;
        <Table as StatefulWidget>::render(table, area, buf, &mut state.table_state);
        let (area, status) = self.status;
        status.render(area, buf);
        if let Some((block, input_box)) = self.input {
            let (area, block) = block;
            block.render(area, buf);
            let (area, input) = input_box;
            <TextInput as StatefulWidgetRef>::render_ref(
                &input, area, buf, &mut state.filename_input_state.as_mut().unwrap()
            );
        }
    }
}
