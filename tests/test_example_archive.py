"""Portable examples seed a fresh database once and preserve later edits."""
import hashlib,json
import duckdb,pytest
from stadtwerke.example_archive import seed_examples


def bundle(tmp_path):
    records=[]
    for index in range(5):
        pdf=tmp_path/f'Geschäftsberichte/Beispiele/report-{index}.pdf'
        pdf.parent.mkdir(parents=True,exist_ok=True);pdf.write_bytes(f'public-example-{index}'.encode())
        rid=hashlib.sha256(pdf.read_bytes()).hexdigest()
        report={'id':rid,'metadata':{'company':f'Versorger {index}','year':2024,'path':pdf.relative_to(tmp_path).as_posix()},'pages':[],'observations':[],'themes':{}}
        analysis=tmp_path/f'data/examples/report-{index}.json';analysis.parent.mkdir(parents=True,exist_ok=True)
        analysis.write_text(json.dumps(report))
        records.append({'id':rid,'pdf':pdf.relative_to(tmp_path).as_posix(),'analysis':analysis.relative_to(tmp_path).as_posix(),'analysis_sha256':hashlib.sha256(analysis.read_bytes()).hexdigest()})
    (tmp_path/'data/example-archive.json').write_text(json.dumps({'reports':records}))
    return records


def db():
    result=duckdb.connect(':memory:')
    result.execute('CREATE TABLE reports (id VARCHAR PRIMARY KEY,metadata JSON,pages JSON,observations JSON,themes JSON)')
    return result


def test_five_examples_import_once_with_relocated_paths(tmp_path):
    records=bundle(tmp_path)
    with db() as connection:
        seed_examples(connection,tmp_path)
        assert connection.execute('SELECT count(*) FROM reports').fetchone()[0]==5
        metadata=json.loads(connection.execute('SELECT metadata FROM reports WHERE id=?',[records[0]['id']]).fetchone()[0])
        assert metadata['example_report'] is True
        assert metadata['path']==str(tmp_path/records[0]['pdf'])
        connection.execute('UPDATE reports SET metadata=? WHERE id=?',[json.dumps({'company':'Reviewed change'}),records[0]['id']])
        seed_examples(connection,tmp_path)
        assert connection.execute('SELECT count(*) FROM reports').fetchone()[0]==5
        assert json.loads(connection.execute('SELECT metadata FROM reports WHERE id=?',[records[0]['id']]).fetchone()[0])['company']=='Reviewed change'


def test_tampered_example_is_not_imported(tmp_path):
    records=bundle(tmp_path)
    (tmp_path/records[0]['analysis']).write_text('{}')
    with db() as connection:
        with pytest.raises(ValueError,match='Prüfsumme'):seed_examples(connection,tmp_path)
        assert connection.execute('SELECT count(*) FROM reports').fetchone()[0]==0
