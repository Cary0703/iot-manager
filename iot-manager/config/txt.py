def fil(x):
    if x == 1:
        return 1
    else:
        return x + fil(x - 1)


print(fil(6))
