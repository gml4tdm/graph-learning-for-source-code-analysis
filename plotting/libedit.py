import collections
import json


class TransformException(Exception):

    def __init__(self, key: str):
        super().__init__(f'Failed to transform {key}')
        self.key = key


def load_raw(filename: str):
    with open(filename) as f:
        data = json.load(f)
    return data


def store_raw(filename: str, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def load(filename: str):
    data = load_raw(filename)
    return resolve(data)


def resolve(data, *, check_rule_applicability=True):
    current = [x for x in data['raw']]
    for rule in data['refinements']:
        match rule['action']:
            case 'refine':
                current, _ = _transform(
                    current, rule['old'], rule['new'], do_raise=check_rule_applicability
                )
            case 'split':
                current, _ = _transform(
                    current, rule['old'], rule['new_1'], rule['new_2'], do_raise=check_rule_applicability
                )
            case 'n-ary-split':
                current, _ = _transform(
                    current, rule['old'], *rule['new'], do_raise=check_rule_applicability
                )
            case _ as x:
                raise NotImplementedError(x)
    return current


def resolve_one(item, refinements):
    return resolve_items([item], refinements)


def resolve_items(items, refinements):
    return resolve({'raw': items, 'refinements': refinements},
                   check_rule_applicability=False)


def resolve_one_with_history(item, refinements):
    current = [item]
    history = [current.copy()]
    for rule in refinements:
        match rule['action']:
            case 'refine':
                current, count = _transform(current, rule['old'], rule['new'], do_raise=False)
            case 'split':
                current, count = _transform(current, rule['old'], rule['new_1'], rule['new_2'], do_raise=False)
            case 'n-ary-split':
                current, count = _transform(current, rule['old'], *rule['new'], do_raise=False)
            case _ as x:
                raise NotImplementedError(x)
        history.append(current.copy())
    return history


def immediate_history(base_key, target_key, refinements):
    current = [base_key]
    result = []
    for rule in refinements:
        match rule['action']:
            case 'refine':
                current, count = _transform(current, rule['old'], rule['new'], do_raise=False)
                if count > 0 and rule['new'] == target_key:
                    result.append(rule['old'])
            case 'split':
                current, count = _transform(current, rule['old'], rule['new_1'], rule['new_2'], do_raise=False)
                if count > 0 and (rule['new_1'] == target_key or rule['new_2'] == target_key):
                    result.append(rule['old'])
            case 'n-ary-split':
                current, count = _transform(current, rule['old'], *rule['new'], do_raise=False)
                if count > 0 and target_key in rule['new']:
                    result.append(rule['old'])
            case _ as x:
                raise NotImplementedError(x)
    return result


def resolve_while(current, refinements, predicate):
    result = []
    for rule in refinements:
        match rule['action']:
            case 'refine':
                current, count = _transform(
                    current, rule['old'], rule['new'], do_raise=False
                )
            case 'split':
                current, count = _transform(
                    current, rule['old'], rule['new_1'], rule['new_2'], do_raise=False
                )
            case 'n-ary-split':
                current, count = _transform(
                    current, rule['old'], *rule['new'], do_raise=False
                )
            case _ as x:
                raise NotImplementedError(x)
        if count == 0:
            continue
        previous = current
        current = []
        for item in previous:
            if predicate(item):
                current.append(item)
            else:
                result.append(item)
    return result


def _transform(current, old, *new, do_raise=True):
    count = current.count(old)
    if count == 0 and do_raise:
        raise TransformException(old)
    current = [x for x in current if x != old]
    for n in new:
        current += [n] * count
    return current, count


def reverse_resolve(data, *to: str):
    result = []
    for item in data['raw']:
        final = resolve_one(item, data['refinements'])
        if any(x in final for x in to):
            result.append(item)
    return result


def reverse_resolve_one(data, *to: str):
    result = []
    for item in data['refinements']:
        match item['action']:
            case 'refine':
                if item['new'] in to:
                    result.append(item['old'])
            case 'split':
                if item['new_1'] in to or item['new_2'] in to:
                    result.append(item['old'])
            case 'n-ary-split':
                if any(x in to for x in item['new']):
                    result.append(item['old'])
            case _ as x:
                raise NotImplementedError(x)
    return result


def count_encountered(data, items):
    counts = collections.defaultdict(int)
    current = [x for x in data['raw']]
    for c in current:
        if c in items:
            counts[c] += 1
    for rule in data['refinements']:
        match rule['action']:
            case 'refine':
                current, count = _transform(current, rule['old'], rule['new'])
                if rule['new'] in items:
                    counts[rule['new']] += count
            case 'split':
                current, count = _transform(current, rule['old'], rule['new_1'], rule['new_2'])
                if rule['new_1'] in items:
                    counts[rule['new_1']] += count
                if rule['new_2'] in items:
                    counts[rule['new_2']] += count
            case 'n-ary-split':
                current, count = _transform(current, rule['old'], *rule['new'])
                for n in rule['new']:
                    if n in items:
                        counts[n] += count
            case _ as x:
                raise NotImplementedError(x)
    return counts


def predicate_replace(filename: str, searcher, replacer):
    data = load(filename)
    rules = []
    for item in set(data):
        if not searcher(item):
            continue
        rule = {
            'action': 'refine',
            'old': item,
            'new': replacer(item)
        }
        rules.append(rule)
    with open(filename, 'r') as file:
        data = json.load(file)
    data['refinements'].extend(rules)
    with open(filename, 'w') as file:
        json.dump(data, file, indent=2)
