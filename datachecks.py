def rate_classification(_code):
    if len(_code) == 5 and _code[2] == '.':
        return 'NL/SfB, 4 cijfers, gescheiden'
    elif len(_code) == 8 and _code[2] == '.' and _code[5] == '.':
        return 'NL/SfB, 6 cijfers, gescheiden'
    elif len(_code) == 9 and _code[2] == '(' and _code[8] == ')':
        return 'NL/SfB, 4 cijfers, haakjes'
    elif len(_code) == 4 and isinstance(_code, int):
        return 'NL/SfB, 4 cijfers, niet gescheiden'
    else:
        return 'Niet gecodeerd'
