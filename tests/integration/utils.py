def simulate_tty(data):
    lines = [" " * 80]
    x = 0
    y = 0

    i = 0
    n = len(data)
    while i < n:
        if data[i] == '\033':
            if data[i + 1] == '[':
                j = i + 2
                while j < n:
                    if not data[j].isdigit():
                        break
                    j = j + 1
                if j == i + 2:
                    # not followed by numbers
                    if data[j] == 'K':
                        lines[y] = " " * 80
                        x = 0
                        i = j + 1
                    else:
                        raise RuntimeError("should be K at {}".format(j))
                else:
                    m = int(data[i + 2:j])
                    if data[j] == 'A':
                        y = y - m
                        i = j + 1
                    elif data[j] == 'B':
                        y = y + m
                        i = j + 1
                    elif data[j] == 'C':
                        x = x + m
                        i = j + 1
                    elif data[j] == 'D':
                        x = x - m
                        i = j + 1
                    elif data[j] == 'm':
                        i = j + 1
                    elif data[j] == ';':
                        k = j + 1
                        while k < n:
                            if not data[k].isdigit():
                                break
                            k = k + 1
                        m2 = int(data[j + 1:k])
                        if data[k] == "m":
                            i = k + 1
                        else:
                            raise RuntimeError("should be m at {}".format(k))
                    else:
                        raise RuntimeError("should be A/B/C/D at {}: {!r}".format(j, data[j - 10: j + 10]))
            else:
                raise RuntimeError("should be [ at {}".format(i + 1))
        elif data[i] == '\r':
            x = 0
            i = i + 1
        elif data[i] == '\n':
            y = y + 1
            i = i + 1
            if y >= len(lines):
                for j in range(len(lines), y + 1):
                    lines.append(" " * 80)
        else:
            if y >= len(lines):
                for j in range(len(lines), y + 1):
                    lines.append(" " * 80)
            line = lines[y]
            line = line[:x] + data[i] + line[x + 1:]
            lines[y] = line
            x = x + 1
            i = i + 1

    return lines
