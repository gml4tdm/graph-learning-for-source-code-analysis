use ratatui::buffer::Buffer;
use ratatui::crossterm::event::{Event, KeyCode, KeyEventKind};
use ratatui::layout::{Alignment, Constraint, Direction, Rect};
use ratatui::prelude::{Color, Layout, Line, Span, StatefulWidget, Style, Stylize, Text};
use ratatui::symbols::border;
use ratatui::widgets::{Block, Clear, Paragraph, Row, StatefulWidgetRef, Table, TableState, WidgetRef, Wrap};
use ratatui::widgets::block::{Position, Title};
use crate::widgets::text_input::{TextInput, TextInputEvent, TextInputState};
use crate::widgets::util::popup::{floating_box, popup};

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Public Tree Constructor
//////////////////////////////////////////////////////////////////////////////////////////////////

#[derive(Debug, Clone)]
pub enum Tree {
    Node{payload: String, children: Vec<Tree>},
    Leaf(String)
}

pub enum ViewerAction {
    Busy,
    Exit,
    Rebuild(String, String)
}

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Private Tree State
//////////////////////////////////////////////////////////////////////////////////////////////////

enum TreeState {
    Node{expanded: bool, children: Vec<TreeState>, text: String},
    Leaf(String)
}

impl TreeState {
    fn from_existing(tree: Tree, old: Self) -> Self {
        Self::from_existing_internal(Self::from(tree), old)
    }
    
    fn from_existing_internal(new: Self, old: Self) -> Self {
        //let new = Self::from(tree);
        match (old, new) {
            (TreeState::Node{expanded: expanded_old, children: children_old, text: text_old}, TreeState::Node{expanded, children, text}) => {
                if text_old == text {
                    TreeState::Node{
                        expanded: expanded_old, 
                        children: children_old.into_iter()
                            .zip(children.into_iter())
                            .map(|(old, new)| Self::from_existing_internal(new, old))
                            .collect(),
                        text
                    }
                } else {
                    TreeState::Node{expanded: false, children, text}
                }
            }
            (TreeState::Leaf(_), TreeState::Node{expanded, children, text}) => {
                TreeState::Node{expanded, children, text}
            },
            (TreeState::Node{..}, TreeState::Leaf(s)) => TreeState::Leaf(s),
            (TreeState::Leaf(_), TreeState::Leaf(s)) => TreeState::Leaf(s),
        }
    }
    
    fn expanded_depth(&self) -> usize {
        match self {
            TreeState::Node{expanded, children, ..} => {
                if *expanded {
                    1 + children.iter().map(|c| c.expanded_depth()).max().unwrap_or(0)
                } else {
                    0
                }
            },
            TreeState::Leaf(_) => 0
        }
    }
    
    fn count_expanded(&self) -> usize {
        match self {
            TreeState::Node{expanded, children, ..} => {
                if *expanded {
                    1 + children.iter().map(|c| c.count_expanded()).sum::<usize>()
                } else {
                    1
                }
            },
            TreeState::Leaf(_) => 1
        }
    }
    
    fn toggle_expand_recursive(&mut self, flag: bool) {
        match self {
            TreeState::Node{expanded, children, ..} => {
                *expanded = flag;
                for child in children {
                    child.toggle_expand_recursive(flag);
                }
            },
            TreeState::Leaf(_) => {}
        }
    }
    
    fn apply_to_node_in_sequence<F>(&mut self, index: usize, f: F)
    where F: Fn(&mut Self)
    {
        let mut found = false;
        let _ = self._apply_to_node_in_sequence(index, &mut found, &f);
    }
    
    fn _apply_to_node_in_sequence<F>(&mut self, mut index: usize, found: &mut bool, f: &F) -> usize
    where F: Fn(&mut Self)
    {
        if index == 0 {
            f(self);
            *found = true;
            0
        } else {
            index -= 1;
            match self {
                TreeState::Node{children, expanded, ..} => {
                    if *expanded {
                        for child in children {
                            index = child._apply_to_node_in_sequence(index, found, f);
                            if *found {
                                break;
                            }
                        }
                    }
                    index
                },
                TreeState::Leaf(_) => index
            }
        }
    }
    
    fn iter_traverse_expanded<F, T>(&self, f: F) -> Vec<(usize, T)>
        where F: Fn(&Self) -> T 
    {
        let mut buffer = Vec::new();
        self._iter_traverse_expanded(&mut buffer, 0, &f);
        buffer 
    }

    fn _iter_traverse_expanded<F, T>(&self, state: &mut Vec<(usize, T)>, depth: usize, f: &F) 
        where F: Fn(&Self) -> T
    {
        let t = f(self);
        state.push((depth, t));
        if let TreeState::Node{children, expanded, ..} = self {
            if *expanded {
                for child in children {
                    child._iter_traverse_expanded(state, depth + 1, f);
                }   
            }
        }
    }
}

impl From<Tree> for TreeState {
    fn from(value: Tree) -> Self {
        match value {
            Tree::Node{payload, mut children} => {
                children.sort_by_key(|c| match c {
                    Tree::Node{payload, ..} => payload.clone(),
                    Tree::Leaf(payload) => payload.clone()
                });
                TreeState::Node{
                    expanded: false,
                    children: children.into_iter().map(|c| c.into()).collect(),
                    text: payload
                }
            }
            Tree::Leaf(payload) => TreeState::Leaf(payload)
        }
    }
}

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Tree View State
//////////////////////////////////////////////////////////////////////////////////////////////////

pub struct TreeViewState {
    tree: TreeState,
    table_state: TableState,
    show_selected_in_window: bool,
    scroll: Option<(String, u16)>,
    editor: Option<TextInputState>
}

impl TreeViewState {
    pub fn new(tree: Tree) -> Self {
        let tree = TreeState::from(tree);
        let mut table_state = TableState::default();
        table_state.select(Some(0));
        Self {
            tree: tree,
            table_state,
            show_selected_in_window: false,
            scroll: None,
            editor: None
        }
    }
    
    pub fn from_tree_and_state(tree: Tree, state: Self) -> Self {
        let tree = TreeState::from_existing(tree, state.tree);
        let mut table_state = TableState::default();
        table_state.select(state.table_state.selected());
        Self {
            tree: tree,
            table_state,
            show_selected_in_window: false,
            scroll: None,
            editor: None
        }
    }
}

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Tree View
//////////////////////////////////////////////////////////////////////////////////////////////////

pub struct TreeView {
}

impl TreeView {
    pub fn new() -> Self {
        Self {
        }
    }
    
    pub fn handle_key_events(&self, state: &mut TreeViewState, event: Event) -> ViewerAction {
        if let Some(editor) = &mut state.editor {
            match TextInput::new().handle_events(event, editor) {
                TextInputEvent::Cancel => {
                    let _ = state.editor.take();
                }
                TextInputEvent::Typed(s) => {
                    let _ = state.editor.take();
                    // so what now?
                    // Enter transition: current -> s
                    // Enter transition: s -> current.parent
                    // Delete transition: current -> current.parent (if not exists)
                    // We might as well assume that we have to redraw the tree.
                    let linearised = state.tree.iter_traverse_expanded(|node| match node {
                        TreeState::Node{text, .. } => text.clone(),
                        TreeState::Leaf(text) => text.clone()
                    });
                    let selection_text = linearised.iter().enumerate()
                        .find(|(i, (_, text))| state.table_state.selected() == Some(*i))
                        .map(|(_, (_, text))| text.clone())
                        .expect("No selection");
                    return ViewerAction::Rebuild(selection_text, s);
                }
                _ => {}
            }
            return ViewerAction::Busy;
        }
        match event {
            Event::Key(inner) if inner.kind == KeyEventKind::Press => {
                match inner.code {
                    KeyCode::Up => {
                        let sel = state.table_state.selected()
                            .expect("No selection");
                        if sel > 0 {
                            state.table_state.select(Some(sel - 1));
                        }
                        ViewerAction::Busy
                    }
                    KeyCode::Down => {
                        let sel = state.table_state.selected()
                            .expect("No selection");
                        if sel < state.tree.count_expanded() - 1 {
                            state.table_state.select(Some(sel + 1));
                        }
                        ViewerAction::Busy
                    }
                    KeyCode::Left => {
                        let sel = state.table_state.selected()
                            .expect("No selection");
                        state.tree.apply_to_node_in_sequence(
                            sel, |node| {
                                if let TreeState::Node{expanded, ..} = node {
                                    *expanded = false;
                                }
                            });
                        ViewerAction::Busy
                    }
                    KeyCode::Char('c') => {
                        let sel = state.table_state.selected()
                            .expect("No selection");
                        state.tree.apply_to_node_in_sequence(
                            sel, |node| {
                                if let TreeState::Node{ .. } = node {
                                    node.toggle_expand_recursive(false)
                                }
                            });
                        ViewerAction::Busy
                    }
                    KeyCode::Char('w') => {
                        state.show_selected_in_window = !state.show_selected_in_window;
                        if !state.show_selected_in_window {
                            let _ = state.scroll.take();
                        }
                        ViewerAction::Busy
                    }
                    KeyCode::Char('a') => {
                        if let Some((_text, scroll)) = &mut state.scroll {
                            if *scroll > 0 {
                                *scroll -= 1;
                            }
                        }
                        ViewerAction::Busy
                    }
                    KeyCode::Char('d') => {
                        if let Some((_text, scroll)) = &mut state.scroll {
                            *scroll += 1;
                        }
                        ViewerAction::Busy
                    }
                    KeyCode::Char('e') => {
                        state.editor = Some(TextInputState::new());
                        ViewerAction::Busy
                    }
                    KeyCode::Right => {
                        let sel = state.table_state.selected()
                            .expect("No selection");
                        state.tree.apply_to_node_in_sequence(
                            sel, |node| {
                                if let TreeState::Node{expanded, ..} = node {
                                    *expanded = true;
                                }
                            });
                        ViewerAction::Busy
                    }
                    KeyCode::Esc => ViewerAction::Exit,
                    _ => ViewerAction::Busy
                }
            }
            _ => ViewerAction::Busy
        }
    }
}

impl Default for TreeView {
    fn default() -> Self {
        Self::new()
    }
}

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Tree View Widget
//////////////////////////////////////////////////////////////////////////////////////////////////

impl StatefulWidgetRef for TreeView {
    type State = TreeViewState;

    fn render_ref(&self, area: Rect, buf: &mut Buffer, state: &mut Self::State) {
        const INDENT_SIZE: usize = 4;
        let linearised = state.tree.iter_traverse_expanded(|node| match node {
            TreeState::Node{text, expanded, ..} => {
                let t = text.clone();
                if *expanded { format!("\u{25BC} {t}") } else { format!("\u{25B6} {t}") }
            },
            TreeState::Leaf(text) => text.clone()
        });
        let selection_text = linearised.iter().enumerate()
            .find(|(i, (_, text))| state.table_state.selected() == Some(*i))
            .map(|(_, (_, text))| text.clone())
            .expect("No selection");
        let table = Table::new(
            linearised.into_iter()
                .enumerate()
                .map(|(k, (indent, text))| {
                    let row_style = if k % 2 == 0 {
                        Style::new().fg(Color::White).bg(Color::DarkGray)
                    } else {
                        Style::new().fg(Color::White).bg(Color::Black)
                    };
                    let r = Row::new(vec![
                        Span::raw(format!("{}{text}", " ".repeat(indent * INDENT_SIZE))),
                    ]).style(row_style);
                    Some(r)
                })
                .filter_map(|o| o),
            [
                Constraint::Percentage(100)
            ]
        );
        let mut table = table
            .highlight_style(Style::new().bg(Color::LightMagenta).bold());
        let instructions = Title::from(
            Line::from(
                vec![
                    " Up/Down ".into(),
                    "<\u{2191}/\u{2193}>".blue().bold(),
                    " Expand/Collapse ".into(),
                    "<\u{2190}/\u{2192}>".blue().bold(),
                    " Collapse Tree ".into(),
                    "<c>".blue().bold(),
                    " View Node in Window ".into(),
                    "<w>".blue().bold(),
                    " Exit ".into(),
                    "<Esc> ".blue().bold(),
                ]
            )
        );
        let block = Block::bordered()
            .title(Title::from(" Tree Viewer ".bold()).alignment(Alignment::Center))
            .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
            .border_set(border::THICK);
        table = table.block(block);
        <Table as StatefulWidget>::render(table, area, buf, &mut state.table_state);

        if state.show_selected_in_window {
            let target_area = floating_box(
                area,
                [Constraint::Percentage(50), Constraint::Percentage(50), Constraint::Percentage(0)],
                [Constraint::Percentage(10), Constraint::Percentage(80), Constraint::Percentage(10)],
            );
            let instructions = Title::from(
                Line::from(
                    vec![
                        " Up/Down ".into(),
                        "<a/d>".blue().bold(),
                        " Exit ".into(),
                        "<w> ".blue().bold(),
                    ]
                )
            );
            let block = Block::bordered()
                .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
                .border_set(border::THICK);
            Clear.render_ref(target_area, buf);
            block.render_ref(target_area, buf);
            let text_area = block.inner(target_area);
            let text = Paragraph::new(
                Text::from(
                    Span::styled(
                        selection_text.clone(),
                        Style::default().fg(Color::White).bg(Color::Black),
                    )
                )
            );
            let scroll = if let Some((text, scroll)) = &state.scroll {
                if text == &selection_text {
                    *scroll
                } else {
                    0
                }
            } else {
                0
            };
            state.scroll = Some((selection_text, scroll));
            let text = text.wrap(Wrap { trim: true }).scroll((scroll, 0));
            text.render_ref(text_area, buf);
        }
        
        if let Some(editor) = &mut state.editor {
            let editor_area = popup(
                area,
                Constraint::Percentage(30),
                Constraint::Length(3)
            );
            let instructions = Title::from(
                Line::from(
                    vec![
                        " Submit ".into(),
                        "<Enter>".blue().bold(),
                        " Exit ".into(),
                        "<Esc> ".blue().bold(),
                    ]
                )
            );
            let block = Block::bordered()
                .title(Title::from(" Tag Editor ".bold()).alignment(Alignment::Center))
                .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
                .border_set(border::THICK);
            let inner = block.inner(editor_area);
            Clear.render_ref(editor_area, buf);
            block.render_ref(editor_area, buf);
            TextInput::new().render_ref(inner, buf, editor);
        }
    }
}

impl StatefulWidget for &TreeView {
    type State = TreeViewState;

    fn render(self, area: Rect, buf: &mut Buffer, state: &mut Self::State) {
        self.render_ref(area, buf, state);
    }
}