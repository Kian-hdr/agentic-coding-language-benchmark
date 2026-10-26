import heapq
import json
import sys


ASCII_WHITESPACE = " \t\n\r\v\f"


def ledger(request: dict) -> dict:
    seen = set()
    accounts = {}
    for entry in request["entries"]:
        identifier = entry["id"]
        if identifier in seen:
            continue
        seen.add(identifier)
        account = entry["account"].strip(ASCII_WHITESPACE)
        if not account:
            return {"error": "empty_account"}
        balance, count = accounts.get(account, (0, 0))
        accounts[account] = (balance + entry["amount"], count + 1)
    return {
        "accounts": [
            {"account": name, "balance": accounts[name][0], "count": accounts[name][1]}
            for name in sorted(accounts)
        ],
        "accepted": len(seen),
    }


def topo(request: dict) -> dict:
    adjacency = {node: set() for node in request["nodes"]}
    indegree = {node: 0 for node in adjacency}
    for source, target in request["edges"]:
        if source not in adjacency or target not in adjacency:
            return {"error": "unknown_node"}
        if target not in adjacency[source]:
            adjacency[source].add(target)
            indegree[target] += 1
    available = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(available)
    order = []
    while available:
        node = heapq.heappop(available)
        order.append(node)
        for target in adjacency[node]:
            indegree[target] -= 1
            if indegree[target] == 0:
                heapq.heappush(available, target)
    if len(order) != len(adjacency):
        return {"error": "cycle"}
    return {"order": order}


class SyntaxFailure(Exception):
    pass


def calc(request: dict) -> dict:
    # Operator/value stacks support deeply nested input without recursion.
    values = []
    operators = []
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2, "u+": 3, "u-": 3}

    def apply() -> None:
        operator = operators.pop()
        if operator in ("u+", "u-"):
            if not values:
                raise SyntaxFailure
            if operator == "u-":
                values[-1] = -values[-1]
            return
        if len(values) < 2:
            raise SyntaxFailure
        right = values.pop()
        left = values.pop()
        if operator == "+":
            result = left + right
        elif operator == "-":
            result = left - right
        elif operator == "*":
            result = left * right
        elif operator == "/":
            if right == 0:
                raise ZeroDivisionError
            quotient = abs(left) // abs(right)
            result = -quotient if (left < 0) != (right < 0) else quotient
        else:
            raise SyntaxFailure
        values.append(result)

    expression = request["expr"]
    position = 0
    expect_operand = True
    try:
        while position < len(expression):
            token = expression[position]
            if token in ASCII_WHITESPACE:
                position += 1
                continue
            if "0" <= token <= "9":
                if not expect_operand:
                    raise SyntaxFailure
                # Accumulate explicitly, allowing arbitrary leading zeroes.
                value = 0
                while position < len(expression) and "0" <= expression[position] <= "9":
                    value = value * 10 + ord(expression[position]) - ord("0")
                    position += 1
                values.append(value)
                expect_operand = False
                continue
            if token == "(":
                if not expect_operand:
                    raise SyntaxFailure
                operators.append(token)
            elif token == ")":
                if expect_operand:
                    raise SyntaxFailure
                while operators and operators[-1] != "(":
                    apply()
                if not operators:
                    raise SyntaxFailure
                operators.pop()
            elif token in "+-*/":
                if expect_operand:
                    if token not in "+-":
                        raise SyntaxFailure
                    operators.append("u" + token)
                else:
                    while (operators and operators[-1] != "("
                           and precedence[operators[-1]] >= precedence[token]):
                        apply()
                    operators.append(token)
                    expect_operand = True
            else:
                raise SyntaxFailure
            position += 1
        if expect_operand:
            raise SyntaxFailure
        while operators:
            if operators[-1] == "(":
                raise SyntaxFailure
            apply()
        if len(values) != 1:
            raise SyntaxFailure
        return {"value": values[0]}
    except SyntaxFailure:
        return {"error": "syntax"}
    except ZeroDivisionError:
        return {"error": "division_by_zero"}


def merge(request: dict) -> dict:
    intervals = request["intervals"]
    if any(start > end for start, end in intervals):
        return {"error": "invalid_interval"}
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return {"intervals": merged}


def respond(request: dict) -> dict:
    operation = {"ledger": ledger, "topo": topo, "calc": calc,
                 "merge": merge}.get(request.get("op"))
    if operation is None:
        return {"error": "unknown_op"}
    return operation(request)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as request_file:
        request = json.load(request_file)
    print(json.dumps(respond(request)))
