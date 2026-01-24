import json
from pathlib import Path
from typing import Any, Optional


def read_json_safe(file_path: str, default: Optional[Any] = None, encoding: str = 'utf-8') -> Any:
    """
    Lee un archivo JSON de forma segura manejando errores comunes.
    
    Args:
        file_path: Ruta al archivo JSON
        default: Valor por defecto a retornar en caso de error (None por defecto)
        encoding: Codificación del archivo (utf-8 por defecto)
    
    Returns:
        Contenido del archivo JSON parseado, o el valor default si hay error
    
    Raises:
        ValueError: Si file_path está vacío
    """
    if not file_path or not file_path.strip():
        raise ValueError("La ruta del archivo no puede estar vacía")
    
    path = Path(file_path)
    
    try:
        # Verificar que el archivo existe
        if not path.exists():
            print(f"Advertencia: El archivo '{file_path}' no existe")
            return default
        
        # Verificar que es un archivo (no un directorio)
        if not path.is_file():
            print(f"Advertencia: '{file_path}' no es un archivo")
            return default
        
        # Leer y parsear el archivo JSON
        with path.open('r', encoding=encoding) as file:
            return json.load(file)
            
    except json.JSONDecodeError as e:
        print(f"Error al parsear JSON en '{file_path}': {e}")
        return default
    
    except PermissionError:
        print(f"Error: No hay permisos para leer '{file_path}'")
        return default
    
    except UnicodeDecodeError as e:
        print(f"Error de codificación al leer '{file_path}': {e}")
        return default
    
    except Exception as e:
        print(f"Error inesperado al leer '{file_path}': {type(e).__name__}: {e}")
        return default


if __name__ == "__main__":
    # Ejemplos de uso
    
    # Ejemplo 1: Leer archivo que existe
    data = read_json_safe("config.json", default={})
    print(f"Datos leídos: {data}")
    
    # Ejemplo 2: Leer archivo que no existe, con valor por defecto
    data = read_json_safe("archivo_inexistente.json", default={"error": "no encontrado"})
    print(f"Con default: {data}")
    
    # Ejemplo 3: Leer con lista como valor por defecto
    items = read_json_safe("items.json", default=[])
    print(f"Items: {items}")
