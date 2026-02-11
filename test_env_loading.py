"""
.envファイル読み込み機能のテストスクリプト
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

from src.core.config import Settings

def test_env_loading():
    """
    .envファイルから環境変数が正しく読み込まれることをテスト
    """
    print("=" * 60)
    print("環境変数読み込みテスト")
    print("=" * 60)
    
    # Settingsをロード（この時点で.envが読み込まれる）
    settings = Settings.load()
    
    # 環境変数が読み込まれたか確認
    git_token = os.environ.get("GIT_ACCESS_TOKEN")
    print(f"\n1. 環境変数 GIT_ACCESS_TOKEN: {git_token if git_token else '(未設定)'}")
    
    # Settingsオブジェクトの内容を確認
    print(f"\n2. Settings.git.accessToken: {settings.git.accessToken if settings.git.accessToken else '(未設定)'}")
    
    # サーバー設定を確認
    print(f"\n3. Server設定:")
    print(f"   - host: {settings.server.host}")
    print(f"   - port: {settings.server.port}")
    print(f"   - workspace: {settings.server.workspace}")
    
    # ジョブ設定を確認
    print(f"\n4. Jobs設定:")
    if settings.jobs:
        for i, job in enumerate(settings.jobs, 1):
            print(f"   Job {i}:")
            print(f"     - name: {job.name}")
            print(f"     - repo_url: {job.repo_url}")
            print(f"     - target_branch: {job.target_branch}")
            print(f"     - script: {job.script}")
    else:
        print("   (ジョブが定義されていません)")
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)
    
    # .envファイルの存在確認
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        print(f"\n[OK] .envファイルが存在します: {env_file}")
    else:
        print(f"\n[WARNING] .envファイルが見つかりません: {env_file}")
        print("  .env_templateをコピーして.envを作成してください")

if __name__ == "__main__":
    test_env_loading()
