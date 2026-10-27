from engine.tokenizer import tokenize
from engine.parser import parse
from engine.evaluator import evaluate

expr = '1 + 1'
tokens = tokenize(expr)
print('tokens:', tokens)
ast = parse(tokens)
print('ast:', ast)
result = evaluate(ast)
print('result:', result)