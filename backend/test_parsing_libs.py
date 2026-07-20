"""
测试简历解析库是否正常工作
"""
import sys

def test_pdfplumber():
    """测试 pdfplumber"""
    try:
        import pdfplumber
        print("[OK] pdfplumber imported successfully")
        version = pdfplumber.__version__ if hasattr(pdfplumber, '__version__') else 'unknown'
        print(f"   Version: {version}")
        return True
    except ImportError as e:
        print(f"[FAIL] pdfplumber import failed: {e}")
        return False

def test_pypdf2():
    """测试 PyPDF2"""
    try:
        import PyPDF2
        print("[OK] PyPDF2 imported successfully")
        version = PyPDF2.__version__ if hasattr(PyPDF2, '__version__') else 'unknown'
        print(f"   Version: {version}")
        return True
    except ImportError as e:
        print(f"[FAIL] PyPDF2 import failed: {e}")
        return False

def test_python_docx():
    """测试 python-docx"""
    try:
        import docx
        print("[OK] python-docx imported successfully")
        version = docx.__version__ if hasattr(docx, '__version__') else 'unknown'
        print(f"   Version: {version}")
        return True
    except ImportError as e:
        print(f"[FAIL] python-docx import failed: {e}")
        return False

def main():
    print("=" * 50)
    print("测试简历解析库")
    print("=" * 50)

    results = []
    results.append(test_pdfplumber())
    results.append(test_pypdf2())
    results.append(test_python_docx())

    print("=" * 50)
    if all(results):
        print("[SUCCESS] All libraries passed the test!")
        return 0
    else:
        print("[FAIL] Some libraries failed the test")
        return 1

if __name__ == "__main__":
    sys.exit(main())
