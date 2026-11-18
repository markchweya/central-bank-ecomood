# Labeller accuracy: local models (Ollama)

Reference labels: 200 paragraphs in [validation/labels.csv](../validation/labels.csv), labelled by Claude Opus 5.5 (not by a person) with the same guide the model gets. Rows of each table are reference labels, columns are model labels.

## Summary

| Model, prompt | Rows | Stance | Outlook | Stance on policy paragraphs | Hawk/dove direction | Outlook direction |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| llama3.2:3b, v1 | all 200 | 22% | 47% | 60% | 7 / 16 | 49 / 55 |
| llama3.2:3b, v2 | 140 held-out (test) | **81%** | 66% | **41%** | 6 / 10 | 9 / 10 |
| gemma4:latest, v2 | 140 held-out (test) | 78% | **70%** | 24% | **4 / 5** | **14 / 15** |

The "direction" columns count only paragraphs where both the reference and the model chose hawkish/dovish (or positive/negative). v2 was tuned on the other 60 rows only.

**Reading it:** v2 fixes the main v1 failure. It now leaves non-policy paragraphs out (99 of 106 correct, against 8 of 138 in v1). It is still weak on the stance of paragraphs that *are* about policy, and it often misses an outlook that is there (28 of 38 positive or negative paragraphs labelled none). With only 13 hawkish or dovish paragraphs in the test rows, the direction numbers are rough.

**gemma4 vs llama3.2 (same v2 prompt, same test rows):** neither is clearly better. gemma4 makes fewer sign errors: it flips hawkish and dovish once, against four times for llama3.2, and finds more of the real outlooks (15 against 10 directional calls, 14 right). But it labels more policy paragraphs as having no stance (14 of 21 neutral ones, against 9), so it covers fewer of them. It is also about 1.5 times slower on this laptop (8-12s a paragraph against about 7s). Both models share the same weak spot, neutral policy paragraphs marked as not about policy, which points at the prompt's topic step rather than the model.

## gemma4:latest, v2, test split

```
ollama / gemma4:latest, prompt v2, test split: 140 reference-labelled paragraphs

stance: accuracy 78%, macro-F1 0.45
model      dovish  hawkish  neutral  none
reference                                
dovish          1        0        1     2
hawkish         1        3        4     1
neutral         1        2        4    14
none            1        0        4   101

outlook: accuracy 70%, macro-F1 0.50
model      negative  neutral  none  positive
reference                                   
negative          7        0    10         0
neutral           5        3     5         3
none              1        3    81         1
positive          1        1    12         7

```

## llama3.2:3b, v2, test split

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

## llama3.2:3b, v1, all rows

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
