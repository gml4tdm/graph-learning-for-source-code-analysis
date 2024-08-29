use std::collections::hash_map::Entry;
use std::collections::{HashMap, HashSet};
use ratatui::crossterm::event::{Event, KeyCode, KeyEventKind};
use ratatui::Frame;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::prelude::{Line, Stylize};
use ratatui::style::{Color, Style};
use ratatui::symbols::border;
use ratatui::text::{Span, Text};
use ratatui::widgets::{Block, Clear, Paragraph, Row, StatefulWidget, StatefulWidgetRef, Table, TableState, Widget};
use ratatui::widgets::block::{Position, Title};
use crate::counter::Counter;
use crate::data::RefinementAction;
use crate::viewer::{Tree, TreeView, TreeViewState};
use crate::widgets::text_input::{TextInput, TextInputEvent, TextInputState};

pub enum EditorEvent {
    Editing,
    Edit{old: usize, new: Vec<String>},
    Exit,
    LockToggle
}

pub enum AnnotationEvent {
    Annotating,
    Cancelled,
    Annotated(Vec<String>)
}


pub fn index_to_string(counter: &Counter<String>, index: usize) -> String {
    let mut order = counter.iter().collect::<Vec<_>>();
    order.sort_by_key(|(entry, _)| *entry);
    order[index].0.clone()
}


pub fn handle_editor_events(event: Event,
                            counter: &mut Counter<String>,
                            actions: Vec<RefinementAction>,
                            locked: &mut HashMap<String, bool>,
                            state: &mut TableState,
                            edit_state: &mut Option<(usize, Vec<TextInputState>)>, 
                            jump_state: &mut Option<TextInputState>,
                            view_state: &mut Option<TreeViewState>) -> EditorEvent {
    if let Some(s) = view_state {
        if TreeView::default().handle_key_events(s, event) {        // true for exit
            let _ = view_state.take();
        }
        return EditorEvent::Editing;
    }
    if let Some(inner) = jump_state {
        match TextInput::new().handle_events(event, inner) {
            TextInputEvent::Cancel => {
                let _ = jump_state.take();
            }
            TextInputEvent::Typing => {}
            TextInputEvent::Typed(position) => {
                if let Ok(mut index) = position.parse::<usize>() {
                    index = index.clamp(1, counter.len()) - 1;
                    state.select(Some(index));
                }
                let _ = jump_state.take();
            }
        }
        return EditorEvent::Editing
    }
    if let Some((sel, inner)) = edit_state {
        let source = index_to_string(counter, state.selected().unwrap());
        match handle_annotation_events(event, sel, inner, source) {
            AnnotationEvent::Annotating => {}
            AnnotationEvent::Cancelled => {
                let _ = edit_state.take();
            }
            AnnotationEvent::Annotated(items) => {
                let _ = edit_state.take();  
                return EditorEvent::Edit {
                    old: state.selected().unwrap(),
                    new: items 
                };
            }
        }
        return EditorEvent::Editing;
    }
    match event {
        Event::Key(key_event) if key_event.kind == KeyEventKind::Press => {
            match key_event.code {
                KeyCode::Char('s') => {
                    let _ = jump_state.insert(TextInputState::new());
                    EditorEvent::Editing
                }
                KeyCode::Char('l') => {
                    let sel = state.selected().unwrap();
                    let key = index_to_string(counter, sel);
                    match locked.entry(key) {
                        Entry::Occupied(e) => {
                            e.remove();
                        }
                        Entry::Vacant(e) => {
                            e.insert(true);
                        }
                    }
                    EditorEvent::LockToggle
                }
                KeyCode::Char('v') => {
                    // build and insert the view state
                    let mut children_by_tag = HashMap::new();
                    for action in actions {
                        let (old, new) = match action {
                            RefinementAction::Refine { old, new } => {
                                (old, HashSet::from([new]))
                            }
                            RefinementAction::Split { old, new_1, new_2 } => {
                                (old, HashSet::from([new_1, new_2]))
                            }
                            RefinementAction::NArySplit { old, new } => {
                                (old, new.into_iter().collect())
                            }
                        };
                        //children_by_tag.entry(old).or_insert_with(HashSet::new).extend(new);
                        for n in new {
                            children_by_tag.entry(n).or_insert_with(HashSet::new).insert(old.clone());
                        }
                    }
                    let mut sorter = topological_sort::TopologicalSort::<String>::new();
                    for (tag, children) in children_by_tag.iter() {
                        for child in children {
                            sorter.add_dependency(child, tag);
                        }
                    }
                    let mut nodes = HashMap::new();
                    loop {
                        let next = sorter.pop_all();
                        if next.is_empty() {
                            break;
                        }
                        for n in next {
                            let depends = children_by_tag.get(&n);
                            match depends {
                                None => {
                                    nodes.insert(n.clone(), Tree::Leaf(n));
                                }
                                Some(children) => {
                                    nodes.insert(
                                        n.clone(),
                                        Tree::Node {
                                            payload: n,
                                            children: children.iter().map(|c| nodes.get(c).unwrap().clone()).collect()
                                        }
                                    );
                                }
                            }
                        }
                    }
                    let root = Tree::Node{
                        payload: "$root".to_string(),
                        children: counter.iter()
                            .map(
                                |(k, _)| nodes.remove(k).unwrap_or_else(
                                    || Tree::Leaf(k.clone())    // never registered because never edited
                                )
                            ).collect()
                    };
                    let state = TreeViewState::new(root);
                    let _ = view_state.insert(state);
                    EditorEvent::Editing
                }
                KeyCode::Up => {
                    let sel = state.selected().unwrap();
                    if sel > 0 {
                        state.select(Some(sel - 1));
                    }
                    EditorEvent::Editing
                }
                KeyCode::Down => {
                    let sel = state.selected().unwrap();
                    if sel < counter.len() - 1 {
                        state.select(Some(sel + 1));
                    }
                    EditorEvent::Editing
                }
                KeyCode::Enter => {
                    let _ = edit_state.insert((0, vec![TextInputState::new()]));
                    EditorEvent::Editing
                }
                KeyCode::Esc => {
                    EditorEvent::Exit
                }
                _ => EditorEvent::Editing
            }
        }
        _ => EditorEvent::Editing
    }
}

fn handle_annotation_events(event: Event, 
                            sel: &mut usize,
                            state: &mut Vec<TextInputState>, 
                            source: String) -> AnnotationEvent {
    match event {
        Event::Key(key_event) if key_event.kind == KeyEventKind::Press => {
            match key_event.code {
                KeyCode::Up => {
                    if *sel > 0 {
                        *sel -= 1;
                    }
                    AnnotationEvent::Annotating
                }
                KeyCode::Down => {
                    if *sel < state.len() - 1 {
                        *sel += 1;
                    }
                    AnnotationEvent::Annotating
                }
                KeyCode::Tab => {
                    state.push(TextInputState::new());
                    *sel = state.len() - 1;
                    AnnotationEvent::Annotating
                }
                KeyCode::Delete => {
                    if state.len() > 1 {
                        state.remove(*sel);
                        if *sel > 0 {
                            *sel -= 1;
                        }
                    }
                    AnnotationEvent::Annotating
                }
                KeyCode::Enter => {
                    AnnotationEvent::Annotated(
                        state.iter()
                            .map(|s| s.get_input())
                            .collect()
                    )
                }
                KeyCode::Esc => {
                    AnnotationEvent::Cancelled
                }
                KeyCode::Insert => {
                    let inp_state = state.get_mut(*sel).unwrap();
                    inp_state.set_input(source);
                    AnnotationEvent::Annotating
                }
                _ => {
                    let inp = TextInput::new();
                    inp.handle_events(event, state.get_mut(*sel).unwrap());
                    AnnotationEvent::Annotating
                }
            }
        }
        _ => AnnotationEvent::Annotating
    }
}


pub fn draw_editor(frame: &mut Frame,
                   counter: &Counter<String>,
                   locked: &mut HashMap<String, bool>,
                   state: &mut TableState, 
                   edit_state: &mut Option<(usize, Vec<TextInputState>)>, 
                   jump_state: &mut Option<TextInputState>,
                   view_state: &mut Option<TreeViewState>) {
    if let Some(s) = view_state {
        TreeView::default()
            .render(frame.size(), frame.buffer_mut(), s)
    } else {
        let area = draw_editor_outer_frame(frame);
        draw_table(area, frame, counter, locked, state);
        if let Some((sel, inner)) = edit_state {
            draw_annotation_box(area, frame, inner, *sel);
        }
        if let Some(inner) = jump_state {
            draw_goto_box(area, frame, counter, inner);
        }
    }
}


fn draw_editor_outer_frame(frame: &mut Frame) -> Rect {
    let instructions = Title::from(
        Line::from(
            vec![
                " Up/Down ".into(),
                "<\u{2191}/\u{2193}>".blue().bold(),
                " Jump To ".into(),
                "<s>".blue().bold(),
                " Lock Entry ".into(),
                "<l>".blue().bold(),
                " Refine ".into(),
                "<Enter>".blue().bold(),
                " Tree View ".into(),
                "<v>".blue().bold(),
                " Esc ".into(),
                "<Esc> ".blue().bold(),
            ]
        )
    );
    let block = Block::bordered()
        .title(Title::from(" Annotating ".bold()).alignment(Alignment::Center))
        .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
        .border_set(border::THICK);
    let inner = block.inner(frame.size());
    block.render(frame.size(), frame.buffer_mut());
    inner
}


fn draw_table(area: Rect,
              frame: &mut Frame,
              counter: &Counter<String>,
              locked: &mut HashMap<String, bool>,
              state: &mut TableState) {
    let mut order = counter.iter().collect::<Vec<_>>();
    order.sort_by_key(|(entry, _)| *entry);
    let table = Table::new(
        order.into_iter()
            .enumerate()
            .map(|(index, (key, value))| {
                // let row_style = if index % 2 == 0 {
                //     Style::new().fg(Color::White).bg(Color::Black)
                // } else {
                //     Style::new().fg(Color::White).bg(Color::DarkGray)
                // };
                let lock = if locked.contains_key(key) {
                    "\u{2705}"
                } else {
                    ""
                };
                let row_style = match (index % 2 == 0, locked.contains_key(key)) {
                    (false, _) => Style::new().fg(Color::White).bg(Color::DarkGray),
                    (true, _) => Style::new().fg(Color::White).bg(Color::Black),
                    //(false, false) => Style::new().fg(Color::White).bg(Color::LightBlue),
                    //(true, false) => Style::new().fg(Color::White).bg(Color::Blue),
                };
                // The larger height mostly just renders incorrectly,
                // but it is convenient for the re-tagging
                let key = Text::raw(format!("{key}"));
                let h = key.height().min(area.height as usize);
                Row::new(vec![
                    Text::raw(format!("{}.", index + 1)),
                    key,
                    Text::raw(format!("{value}")),
                    Text::raw(lock)
                ]).style(row_style).height(h as u16)
            }),
        [
            Constraint::Length(5),
            Constraint::Fill(1),
            Constraint::Length(5),
            Constraint::Length(2)
        ]
    );
    let table = table
        .highlight_style(Style::new().bg(Color::LightRed).bold());
    <Table as StatefulWidget>::render(table, area, frame.buffer_mut(), state);
}

fn draw_goto_box(area: Rect, 
                 frame: &mut Frame, 
                 counter: &Counter<String>,
                 state: &mut TextInputState) 
{
    let title = Title::from(
        format!("Enter Position to Jump to (1 - {})", counter.len()).bold()
    );
    let instructions = Title::from(
        Line::from(vec![
            " Jump ".into(),
            "<Enter>".blue().bold(),
            " Cancel ".into(),
            "<Esc> ".blue().bold(),
        ])
    );
    let block = Block::bordered()
        .title(title.alignment(Alignment::Center))
        .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
        .border_set(border::THICK);
    let area = crate::widgets::util::popup::popup(
        area, Constraint::Percentage(30), Constraint::Length(3)
    );
    let inner = block.inner(area);
    frame.render_widget(Clear, area);
    block.render(area, frame.buffer_mut());
    let inp = TextInput::new();
    inp.render_ref(inner, frame.buffer_mut(), state);
    let (x, y) = inp.cursor(inner, state);
    frame.set_cursor(x, y);
}


fn draw_annotation_box(
    area: Rect,
    frame: &mut Frame,
    state: &mut Vec<TextInputState>,
    current: usize)
{
    let area = crate::widgets::util::popup::floating_box(
        area,
        [
            Constraint::Percentage(60),
            Constraint::Fill(1),
            Constraint::Percentage(1)
        ],
        [
            Constraint::Percentage(1),
            Constraint::Fill(1),
            Constraint::Percentage(1)
        ]
    );
    let instructions = Title::from(
        Line::from(vec![
                " Up/Down ".into(),
                "<\u{2191}/\u{2193}>".blue().bold(),
                " New Option ".into(),
                "<Tab>".blue().bold(),
                " Delete Option ".into(),
                "<Del>".blue().bold(),
                " Submit ".into(),
                "<Enter>".blue().bold(),
                " Cancel ".into(),
                "<Esc> ".blue().bold(),
        ])
    );
    let block = Block::bordered()
        .title(Title::from("Refine Tag".bold()).alignment(Alignment::Center))
        .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
        .border_set(border::THICK);
    let inner = block.inner(area);
    frame.render_widget(Clear, area);
    block.render(area, frame.buffer_mut());
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints((0..state.len()).map(|_| Constraint::Length(1)))
        .split(inner);
    let cursor = state.into_iter()
        .zip(chunks.into_iter())
        .enumerate()
        .map(|(index, (s, &rect))| {
            let chunks = Layout::default()
                .direction(Direction::Horizontal)
                .constraints([
                    Constraint::Length(3),
                    Constraint::Fill(1)
                ])
                .split(rect);
            let p = Paragraph::new(Span::raw(format!("{}.", index + 1)));
            p.render(chunks[0], frame.buffer_mut());
            if index == current {
                let inp = TextInput::new();
                inp.render_ref(chunks[1], frame.buffer_mut(), s);
                Some(inp.cursor(chunks[1], s))
            } else {
                TextInput::new().render_ref(chunks[1], frame.buffer_mut(), s);
                None
            }
        })
        .collect::<Vec<_>>()    // collect to force rendering all widgets     
        .into_iter()
        .find(Option::is_some)
        .unwrap()
        .unwrap();
    frame.set_cursor(cursor.0, cursor.1);
}