use ratatui::buffer::Buffer;
use ratatui::crossterm::event::{Event, KeyCode, KeyEventKind};
use ratatui::layout::{Alignment, Constraint, Rect};
use ratatui::prelude::{Color, Line, Span, StatefulWidget, Style, Stylize};
use ratatui::symbols::border;
use ratatui::widgets::{Block, Row, StatefulWidgetRef, Table, TableState};
use ratatui::widgets::block::{Position, Title};

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Public Tree Constructor
//////////////////////////////////////////////////////////////////////////////////////////////////

#[derive(Debug, Clone)]
pub enum Tree {
    Node{payload: String, children: Vec<Tree>},
    Leaf(String)
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
            Tree::Node{payload, children} => TreeState::Node{
                expanded: false,
                children: children.into_iter().map(|c| c.into()).collect(),
                text: payload
            },
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
    table_state: TableState
}

impl TreeViewState {
    pub fn new(tree: Tree) -> Self {
        let tree = TreeState::from(tree);
        let mut table_state = TableState::default();
        table_state.select(Some(0));
        Self {
            tree: tree,
            table_state
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
    
    pub fn handle_key_events(&self, state: &mut TreeViewState, event: Event) -> bool {
        match event {
            Event::Key(inner) if inner.kind == KeyEventKind::Press => {
                match inner.code {
                    KeyCode::Up => {
                        let sel = state.table_state.selected()
                            .expect("No selection");
                        if sel > 0 {
                            state.table_state.select(Some(sel - 1));
                        }
                        false 
                    }
                    KeyCode::Down => {
                        let sel = state.table_state.selected()
                            .expect("No selection");
                        if sel < state.tree.count_expanded() - 1 {
                            state.table_state.select(Some(sel + 1));
                        }
                        false 
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
                        false
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
                        false
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
                        false 
                    }
                    KeyCode::Esc => true,
                    _ => false
                }
            }
            _ => false
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
    }
}

impl StatefulWidget for &TreeView {
    type State = TreeViewState;

    fn render(self, area: Rect, buf: &mut Buffer, state: &mut Self::State) {
        self.render_ref(area, buf, state);
    }
}