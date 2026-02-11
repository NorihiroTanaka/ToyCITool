import os, stat
import shutil
import time
import logging

logger = logging.getLogger(__name__)

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
            for i in range(3): # 最大3回リトライ
                try:
                    shutil.rmtree(work_dir, onexc=self.remove_readonly)
                    logger.info(f"ワークスペース {work_dir} を削除しました。")
                    return
                except Exception as e:
                    logger.warning(f"ワークスペースの削除に失敗しました (試行 {i+1}/3): {e}")
                    time.sleep(1) # 1秒待機
            
            logger.error(f"ワークスペース {work_dir} の削除に最終的に失敗しました。")
            raise Exception(f"Failed to clean workspace after multiple retries.")