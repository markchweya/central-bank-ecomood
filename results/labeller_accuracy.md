# Labeller accuracy: llama3.2:3b (Ollama)

Reference labels: 200 paragraphs in [validation/labels.csv](../validation/labels.csv), labelled by Claude Opus 5.5 (not by a person) with the same guide the model gets. Rows are reference labels, columns are model labels.

```
ollama / llama3.2:3b on 200 reference-labelled paragraphs

stance: accuracy 22%, macro-F1 0.18
model    dovish  hawkish  neutral  none
ref                                    
dovish        1        7        2     0
hawkish       2        6        3     0
neutral       0       11       30     0
none         15       31       84     8

outlook: accuracy 47%, macro-F1 0.41
model     negative  neutral  none  positive
ref                                        
negative        23        1     0         3
neutral          9        2     0         9
none            38       16    43        25
positive         3        1     1        26

```
