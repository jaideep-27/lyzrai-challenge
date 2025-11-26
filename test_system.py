#!/usr/bin/env python
"""
Quick test script for the PR Review Agent
"""
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_llm():
    """Test LLM connection"""
    print("\n=== Testing LLM Connection ===")
    from app.services.llm_provider import get_llm
    from app.config import settings
    
    if not settings.google_api_key:
        print("❌ GOOGLE_API_KEY not set")
        return False
    
    try:
        llm = get_llm(api_key=settings.google_api_key)
        response = llm.generate("Say 'Hello, I am working!' in exactly those words.")
        print(f"✅ LLM Response: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return False


def test_diff_parser():
    """Test diff parser"""
    print("\n=== Testing Diff Parser ===")
    from app.services.diff_parser import diff_parser
    
    test_diff = """diff --git a/test.py b/test.py
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def hello():
-    print('Hello')
+    print('Hello World')
+    return True
"""
    
    try:
        parsed = diff_parser.parse(test_diff)
        print(f"✅ Parsed {len(parsed)} files")
        print(f"   File: {parsed[0].file_path}")
        print(f"   Language: {parsed[0].language}")
        print(f"   Additions: {parsed[0].additions}")
        print(f"   Deletions: {parsed[0].deletions}")
        return True
    except Exception as e:
        print(f"❌ Diff Parser Error: {e}")
        return False


def test_database():
    """Test database"""
    print("\n=== Testing Database ===")
    from app.models.database import init_db, create_session, PullRequestReview
    from app.config import settings
    
    try:
        engine = init_db(settings.database_url)
        SessionLocal = create_session(engine)
        db = SessionLocal()
        
        # Count reviews
        count = db.query(PullRequestReview).count()
        print(f"✅ Database connected. {count} existing reviews.")
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False


def test_review():
    """Test the full review workflow"""
    print("\n=== Testing Review Workflow ===")
    from app.orchestrator import create_orchestrator
    from app.config import settings
    
    test_diff = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,10 +1,15 @@
 import os
+import subprocess
 
 def get_user_data(user_id):
-    query = "SELECT * FROM users WHERE id = " + user_id
+    query = f"SELECT * FROM users WHERE id = {user_id}"
     return execute_query(query)
 
+def run_command(cmd):
+    os.system(cmd)
+    return subprocess.call(cmd, shell=True)
+
 def process_data(data):
     result = []
     for i in range(len(data)):
"""
    
    try:
        orchestrator = create_orchestrator(
            llm_api_key=settings.google_api_key,
            github_token=None
        )
        
        result = orchestrator.review_diff(test_diff, parallel=False)
        
        print(f"✅ Review completed")
        print(f"   Files reviewed: {result.get('files_reviewed', 0)}")
        print(f"   Findings: {len(result.get('findings', []))}")
        
        if result.get('findings'):
            print("\n   Sample findings:")
            for i, finding in enumerate(result['findings'][:3]):
                print(f"   {i+1}. [{finding.get('severity', '?')}] {finding.get('title', 'Unknown')}")
        
        return True
    except Exception as e:
        print(f"❌ Review Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("PR Review Agent - System Test")
    print("=" * 50)
    
    results = {
        "Database": test_database(),
        "Diff Parser": test_diff_parser(),
        "LLM": test_llm(),
    }
    
    # Only test review if LLM works
    if results["LLM"]:
        results["Review Workflow"] = test_review()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("All tests passed! 🎉" if all_passed else "Some tests failed. Check output above."))
