use std::collections::HashMap;
use std::path::Path;
use anyhow::anyhow;
use crate::counter::Counter;

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct RefinementData {
    raw: Vec<String>,
    refinements: Vec<RefinementAction>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub locked: Option<HashMap<String, bool>>
}


#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[derive(PartialEq, Eq)]
#[serde(tag = "action")]
pub enum RefinementAction {
    #[serde(rename = "refine")]
    Refine{old: String, new: String},

    #[serde(rename = "split")]
    Split{old: String, new_1: String, new_2: String},

    #[serde(rename = "n-ary-split")]
    NArySplit{old: String, new: Vec<String>}
}


impl RefinementData {
    
    pub fn refinements(&self) -> &[RefinementAction] {
        &self.refinements
    }
    
    pub fn load_from_file(path: &Path) -> anyhow::Result<Self> {
        let file = std::fs::File::open(path)?;
        let reader = std::io::BufReader::new(file);
        let mut data: RefinementData = serde_json::from_reader(reader)?;
        if data.locked.is_none() {
            data.locked = Some(HashMap::new());
        }
        Ok(data)
    }
    
    pub fn store_to_file(&self, path: &Path) -> anyhow::Result<()> {
        let file = std::fs::File::create(path)?;
        let writer = std::io::BufWriter::new(file);
        serde_json::to_writer_pretty(writer, self)?;
        Ok(())
    }
    
    pub fn get_refined(&self) -> anyhow::Result<Counter<String>> {
        let mut counter = Counter::new();
        for entry in self.raw.iter().cloned() {
            let _ = counter.add(entry);
        }
        for refinement in self.refinements.iter() {
            match refinement {
                RefinementAction::Refine { old, new } => {
                    refine_helper(&mut counter, old.clone(), [new].into_iter().cloned())?;
                }
                RefinementAction::Split { old, new_1, new_2 } => {
                    refine_helper(&mut counter, old.clone(), [new_1, new_2].into_iter().cloned())?;
                }
                RefinementAction::NArySplit { old, new } => {
                    refine_helper(&mut counter, old.clone(), new.iter().cloned())?;
                }
            }
        }
        Ok(counter)
    }
    
    pub fn update_refine(&mut self, 
                         counter: &mut Counter<String>, 
                         old: String, 
                         new: String) -> anyhow::Result<()> 
    {
        self.refinements.push(RefinementAction::Refine {old: old.clone(), new: new.clone()});
        refine_helper(counter, old.clone(), [new].into_iter())
    }
    
    pub fn update_split(&mut self, 
                        counter: &mut Counter<String>,
                        old: String,
                        new_1: String,
                        new_2: String) -> anyhow::Result<()> {
        self.refinements.push(RefinementAction::Split {old: old.clone(), new_1: new_1.clone(), new_2: new_2.clone()});
        refine_helper(counter, old.clone(), [new_1, new_2].into_iter())
    }
    
    pub fn update_n_ary_split(&mut self,
                              counter: &mut Counter<String>,
                              old: String,
                              new: Vec<String>) -> anyhow::Result<()> {
        self.refinements.push(RefinementAction::NArySplit {old: old.clone(), new: new.clone()});
        refine_helper(counter, old.clone(), new.into_iter())
    }
    
    pub fn insert_refinement(&mut self, old_key: String, new_key: String) {
        // First, check that there exists a unique "Refine" action for the old key 
        let old_actions = self.refinements.iter()
            .enumerate()
            .filter(|(i, action)| match action {
                RefinementAction::Refine { old, .. } => old == &old_key,
                _ => false
            })
            .collect::<Vec<_>>();
        if old_actions.len() > 1 {
            panic!("Multiple Refine actions for {old_key}");
        }
        // Get the original parent 
        let (index, action) = old_actions.first().unwrap();
        let old_parent = match action {
            RefinementAction::Refine { old, new } => new.clone(),
            _ => panic!("No Refine action for {old_key}")
        };
        // Remove the original refinement 
        let index= *index;
        // Remove the old action
        //eprintln!("Removing action: {:?}", self.refinements[index]);
        self.refinements.remove(index);
        // Insert the new actions
        //eprintln!("Pushing action: Refine {} -> {}", old_key, new_key);
        self.refinements.insert(index, RefinementAction::Refine { 
            old: old_key, 
            new: new_key.clone() 
        });
        //eprintln!("Pushing action: Refine {} -> {}", new_key, old_parent);
        let refinement = RefinementAction::Refine { old: new_key, new: old_parent };
        if !self.refinements.contains(&refinement) {
            self.refinements.insert(index + 1, refinement);
        }
        // Note that this does not actually update the counter
    }
}

fn refine_helper(counter: &mut Counter<String>, 
                 old: String,    
                 new: impl Iterator<Item=String>) -> anyhow::Result<()> {
    let previous = counter.delete(&old)
        .ok_or_else(|| anyhow!("Refinement does not apply to any entries"))?;
    for n in new {
        let _ = counter.update_by(n, previous);
    }
    Ok(())
}
