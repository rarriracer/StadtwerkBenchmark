"""One local analysis worker. UI polls memory; worker never touches Streamlit."""
import threading
import time
import uuid


class JobRunner:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs = {}
        self._active = None

    def active(self):
        with self._lock:
            return self._active is not None

    def start(self, operation):
        with self._lock:
            if self._active is not None:
                raise RuntimeError('Eine Analyse läuft bereits. Der Fortschritt wird oben angezeigt.')
            identifier = str(uuid.uuid4())
            self._active = identifier
            self._jobs[identifier] = {'status':'running','started':time.monotonic(),
                'event':{'stage':'document','detail':'Auftrag angenommen · Analyse wird vorbereitet','completed':0,'total':0}}
        thread = threading.Thread(target=self._run,args=(identifier,operation),name='stadtwerke-'+identifier,daemon=True)
        thread.start()
        return identifier

    def snapshot(self, identifier):
        with self._lock:
            job = self._jobs.get(identifier)
            if job is None:
                return None
            return {**job,'event':dict(job['event']),'elapsed':time.monotonic()-job['started']}

    def _run(self, identifier, operation):
        def progress(event):
            with self._lock:
                self._jobs[identifier]['event'] = dict(event)
        try:
            result = operation(progress)
            with self._lock:
                self._jobs[identifier].update(status='done',result=result)
        except Exception as exc:
            with self._lock:
                self._jobs[identifier].update(status='error',error=str(exc))
        finally:
            with self._lock:
                self._active = None
                # Retain recent results, but don't grow indefinitely.
                for key in list(self._jobs)[:-20]:
                    del self._jobs[key]
