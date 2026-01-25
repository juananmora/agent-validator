"""Módulo para lectura segura de archivos JSON."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def read_json_safe(
    file_path: Union[str, Path],
    default: Optional[Any] = None,
    encoding: str = 'utf-8',
    raise_on_error: bool = False
) -> Any:
    """
    Lee un archivo JSON de forma segura manejando errores comunes.
    
    Esta función maneja de forma robusta los errores más comunes al leer
    archivos JSON: archivo no encontrado, JSON inválido, y errores de permisos.
    
    Args:
        file_path: Ruta al archivo JSON (str o Path).
        default: Valor por defecto a retornar en caso de error (None por defecto).
        encoding: Codificación del archivo (utf-8 por defecto).
        raise_on_error: Si True, lanza excepciones en lugar de retornar default.
    
    Returns:
        Contenido del archivo JSON parseado, o el valor default si hay error
        y raise_on_error es False.
    
    Raises:
        ValueError: Si file_path está vacío o no es válido.
        FileNotFoundError: Si el archivo no existe (solo si raise_on_error=True).
        PermissionError: Si no hay permisos de lectura (solo si raise_on_error=True).
        json.JSONDecodeError: Si el JSON es inválido (solo si raise_on_error=True).
        
    Examples:
        >>> data = read_json_safe("config.json", default={})
        >>> users = read_json_safe("users.json", default=[], raise_on_error=True)
    """
    # Validar entrada
    if not file_path:
        raise ValueError("La ruta del archivo no puede estar vacía")
    
    if isinstance(file_path, str):
        if not file_path.strip():
            raise ValueError("La ruta del archivo no puede estar vacía")
        path = Path(file_path)
    else:
        path = file_path
    
    try:
        # Leer y parsear el archivo JSON
        with path.open('r', encoding=encoding) as file:
            return json.load(file)
            
    except FileNotFoundError as e:
        if raise_on_error:
            raise FileNotFoundError(f"Archivo no encontrado: '{path}'") from e
        return default
    
    except json.JSONDecodeError as e:
        if raise_on_error:
            raise json.JSONDecodeError(
                f"JSON inválido en '{path}': {e.msg}",
                e.doc,
                e.pos
            ) from e
        return default
    
    except PermissionError as e:
        if raise_on_error:
            raise PermissionError(f"Sin permisos para leer '{path}'") from e
        return default
    
    except (IsADirectoryError, OSError) as e:
        if raise_on_error:
            raise ValueError(f"'{path}' no es un archivo válido") from e
        return default




if __name__ == "__main__":
    # Ejemplos de uso
    from tempfile import NamedTemporaryFile
    import os
    
    print("=== Ejemplos de uso de read_json_safe ===\n")
    
    # Ejemplo 1: Archivo no encontrado
    print("1. Archivo no encontrado (con default):")
    data = read_json_safe("archivo_inexistente.json", default={"error": "no encontrado"})
    print(f"   Resultado: {data}\n")
    
    # Ejemplo 2: Crear y leer un archivo válido
    print("2. Leer archivo JSON válido:")
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"nombre": "Python", "version": "3.11"}, f)
        temp_file = f.name
    
    try:
        data = read_json_safe(temp_file, default={})
        print(f"   Resultado: {data}\n")
    finally:
        os.unlink(temp_file)
    
    # Ejemplo 3: JSON inválido
    print("3. JSON inválido (con default):")
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{invalid json}")
        temp_file = f.name
    
    try:
        data = read_json_safe(temp_file, default=[])
        print(f"   Resultado: {data}\n")
    finally:
        os.unlink(temp_file)
    
    # Ejemplo 4: Usando raise_on_error
    print("4. Con raise_on_error=True:")
    try:
        data = read_json_safe("inexistente.json", raise_on_error=True)
    except FileNotFoundError as e:
        print(f"   Excepción capturada: {e}\n")
    
    # Ejemplo 5: Usando Path
    print("5. Usando Path en lugar de str:")
    data = read_json_safe(Path("config.json"), default={"default": "config"})
    print(f"   Resultado: {data}\n")
    
    print("=== Fin de los ejemplos ===")
