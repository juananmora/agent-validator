def calcular_fibonacci(n):
    """
    Calcula los primeros n números de la serie de Fibonacci.
    
    Args:
        n: Cantidad de números de Fibonacci a calcular
        
    Returns:
        Lista con los primeros n números de Fibonacci
    """
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fibonacci = [0, 1]
    for i in range(2, n):
        fibonacci.append(fibonacci[i-1] + fibonacci[i-2])
    
    return fibonacci

if __name__ == "__main__":
    resultado = calcular_fibonacci(10)
    print("Los 10 primeros números de la serie de Fibonacci son:")
    print(resultado)
    print(f"\nEn detalle: {', '.join(map(str, resultado))}")
