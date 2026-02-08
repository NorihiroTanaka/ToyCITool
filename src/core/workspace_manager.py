import os, stat
import shutil

class WorkspaceManager:
    def __init__(self, base_dir: str = "./workspace"):
        self.base_dir = os.path.abspath(base_dir)

    def remove_readonly(self, func, path, _):
        """読み取り専用ファイルを削除するためのヘルパー関数"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def prepare_workspace(self, job_name: str) -> str:
        """ワークスペースを準備する (既存なら削除して作成)"""
        work_dir = os.path.join(self.base_dir, job_name)
        
        if os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir, onexc=self.remove_readonly)
            except Exception as e:
                raise Exception(f"Failed to clean workspace: {e}")
                
        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    def cleanup_workspace(self, job_name: str):
        """ワークスペースを削除する"""
        work_dir = os.path.join(self.base_dir, job_name)
        
        if os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir, onexc=self.remove_readonly)
            except Exception as e:
                raise Exception(f"Failed to clean workspace: {e}")