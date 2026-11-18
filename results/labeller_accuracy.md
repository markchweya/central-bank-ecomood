# Labeller accuracy: llama3.2:3b (Ollama)

Reference labels: 200 paragraphs in [validation/labels.csv](../validation/labels.csv), labelled by Claude Opus 5.5 (not by a person) with the same guide the model gets. Rows of each table are reference labels, columns are model labels.

## Summary

| Prompt | Rows | Stance | Outlook | Stance on policy paragraphs | Hawk/dove direction | Outlook direction |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| v1 | all 200 | 22% | 47% | 60% | 7 / 16 | 49 / 55 |
| v2 | 140 held-out (test) | **81%** | **66%** | 41% | 6 / 10 | 9 / 10 |

The "direction" columns count only paragraphs where both the reference and the model chose hawkish/dovish (or positive/negative). v2 was tuned on the other 60 rows only.

**Reading it:** v2 fixes the main v1 failure. It now leaves non-policy paragraphs out (99 of 106 correct, against 8 of 138 in v1). It is still weak on the stance of paragraphs that *are* about policy, and it often misses an outlook that is there (28 of 38 positive or negative paragraphs labelled none). With only 13 hawkish or dovish paragraphs in the test rows, the direction numbers are rough.

## v2, test split

```
ollama / llama3.2:3b, prompt v2, test split: 140 reference-labelled paragraphs

stance: accuracy 81%, macro-F1 0.53
model      dovish  hawkish  neutral  none
reference                                
dovish          1        2        0     1
hawkish         2        5        2     0
neutral         3        1        8     9
none            1        0        6    99

outlook: accuracy 66%, macro-F1 0.40
model      negative  neutral  none  positive
reference                                   
negative          4        0    13         0
neutral           4        2     6         4
none              3        2    81         0
positive          1        0    15         5

```

## v1, all rows

```
ollama / llama3.2:3b on 200 reference-labelled paragraphs

stance: accuracy 22%, macro-F1 0.18
model    dovish  hawkish  neutral  none
reference                              
dovish        1        7        2     0
hawkish       2        6        3     0
neutral       0       11       30     0
none         15       31       84     8

outlook: accuracy 47%, macro-F1 0.41
model     negative  neutral  none  positive
reference                                  
negative        23        1     0         3
neutral          9        2     0         9
none            38       16    43        25
positive         3        1     1        26

```
