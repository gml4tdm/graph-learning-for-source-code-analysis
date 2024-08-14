use ratatui::buffer::Buffer;
use ratatui::layout::Rect;
use ratatui::style::Style;
use ratatui::text::Span;
use ratatui::widgets::{Paragraph, StatefulWidgetRef, Widget};

use super::input::Command;
use super::state::TextInputState;

pub enum TextInputEvent {
    Cancel,
    Typing,
    Typed(String)
}

pub struct TextInput {
    style: Option<Style>
}

#[allow(unused)]
impl TextInput {
    pub fn new() -> Self {
        TextInput { style: None }
    }

    pub fn with_style(mut self, style: Style) -> Self {
        self.style = Some(style);
        self
    }

    pub fn cursor(&self, area: Rect, state: &TextInputState) -> (u16, u16) {
        let x = area.x + state.cursor;
        let y = area.y;
        (x, y)
    }

    pub fn handle_events(&self,
                         event: impl Into<Command>,
                         state: &mut TextInputState) -> TextInputEvent
    {
        match event.into() {
            Command::CursorLeft => {
                state.cursor_left();
                TextInputEvent::Typing
            },
            Command::CursorRight => {
                state.cursor_right();
                TextInputEvent::Typing
            },
            Command::Submit => {
                TextInputEvent::Typed(state.get_input())
            },
            Command::Cancel => TextInputEvent::Cancel,
            Command::DeleteCharacter => {
                state.backspace();
                TextInputEvent::Typing
            },
            Command::InsertCharacter(c) => {
                state.insert(c);
                TextInputEvent::Typing
            },
            Command::NoAction => {
                TextInputEvent::Typing
            }
        }
    }
}

impl StatefulWidgetRef for TextInput {
    type State = TextInputState;

    fn render_ref(&self, area: Rect, buf: &mut Buffer, state: &mut Self::State) {
        let text = match self.style {
            Some(ref style) => Span::styled(state.get_input(), style.clone()),
            None => Span::raw(state.get_input())
        };
        let p = Paragraph::new(text);
        <Paragraph as Widget>::render(p, area, buf);
    }
}