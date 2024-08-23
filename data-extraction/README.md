# !Important Notes About Tags! 

The tags contained in the files here, including the `data.json` files,
were slightly further simplified for presentation in the paper. 
Specifically, we applied the following further simplifications:


### Model Tags 

```
gnn-functionality: gnn: custom edge-type aware message passing scheme --> gnn-functionality: gnn: custom GNN layer
gnn-functionality: gnn: custom message passing scheme --> gnn-functionality: gnn: custom GNN layer
gnn-functionality: gnn: custom edge-type aware message passing scheme w. attention --> gnn-functionality: gnn: custom GNN layer
```

``` 
gnn-functionality: tree: transformer (first bottom up w. attention, then top down without attention) --> gnn-functionality: tree: tree transformer
gnn-functionality: tree: tree-lstm variant --> gnn-functionality: tree: tree-LSTM
gnn-functionality: tree: tree-lstm --> gnn-functionality: tree: tree-LSTM
gnn-functionality: tree: child-sum tree-lstm --> gnn-functionality: tree: tree-LSTM
gnn-functionality: tree: recursively applied bottom-up auto-encoder for node embeddings --> gnn-functionality: tree: recursive bottom-up auto-encoder
gnn-functionality: tree: cnn over sequence, but based on original tree structure --> gnn-functionality: tree: tree adjusted CNN
```

``` 
gnn-functionality: pooling: graph paths: mean pooling --> gnn-functionality: pooling: summing: mean pooling
gnn-functionality: pooling: graph: attention weighted sum --> gnn-functionality: pooling: summing: attention weighted sum
gnn-functionality: pooling: graph: bidirectional lstm --> gnn-functionality: pooling: misc: bidirectional lstm
gnn-functionality: pooling: graph: combined sum and max pooling --> gnn-functionality: pooling: misc: combined sum and max pooling
gnn-functionality: pooling: graph: conv w. max pooling over node feature matrix --> gnn-functionality: pooling: misc: conv w. max pooling over node feature matrix
gnn-functionality: pooling: graph: dmonpooling --> gnn-functionality: pooling: graph coarsening: DMoNPool
gnn-functionality: pooling: graph: dynamic pooling --> gnn-functionality: pooling: misc: max pooling
gnn-functionality: pooling: graph: edge pooling --> gnn-functionality: pooling: graph coarsening: edge pooling
gnn-functionality: pooling: graph: global attention pooling --> gnn-functionality: pooling: summing: global attention pooling
gnn-functionality: pooling: graph: graph pooling (reduce nodes by half) --> gnn-functionality: pooling: node sampling: unspecified
gnn-functionality: pooling: graph: h-sagpool --> gnn-functionality: pooling: node sampling: SAGPool
gnn-functionality: pooling: graph: hierarchical self-attention graph pooling --> gnn-functionality: pooling: node sampling: SAGPool
gnn-functionality: pooling: graph: max pooling --> gnn-functionality: pooling: misc: max pooling
gnn-functionality: pooling: graph: mean biaffine attention pooling --> gnn-functionality: pooling: misc: mean bi-affine attention pooling
gnn-functionality: pooling: graph: mean pooling --> gnn-functionality: pooling: summing: mean pooling
gnn-functionality: pooling: graph: mincutpool --> gnn-functionality: pooling: graph coarsening: MinCutPool
gnn-functionality: pooling: graph: sagpool --> gnn-functionality: pooling: node sampling: SAGPool
gnn-functionality: pooling: graph: set2set --> gnn-functionality: pooling: misc: set2set
gnn-functionality: pooling: graph: sigmoid attention sum --> gnn-functionality: pooling: summing: gated sum
gnn-functionality: pooling: graph: sort pooling --> gnn-functionality: pooling: node sampling: SortPooling
gnn-functionality: pooling: graph: sum pooling --> gnn-functionality: pooling: summing: sum
gnn-functionality: pooling: graph: top-k pooling --> gnn-functionality: pooling: node sampling: top-k pooling
gnn-functionality: pooling: graph: unspecified --> gnn-functionality: pooling: unspecified
gnn-functionality: pooling: graph: weighted sum pooling --> gnn-functionality: pooling: summing: weighted sum
gnn-functionality: pooling: node-type: mean pooling --> gnn-functionality: pooling: summing: mean pooling
gnn-functionality: pooling: tree: bottom-up attention weighted sum of self and child nodes --> gnn-functionality: pooling: summing: attention weighted sum
gnn-functionality: pooling: tree: child-sum pooling --> gnn-functionality: pooling: summing: child-sum
```