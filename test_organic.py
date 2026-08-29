import asyncio
from run_curriculum import WorkerPool
from pathlib import Path

async def test():
    pool = WorkerPool(1)
    await pool.start()
    targets = [
        'hostile/02_irs_1040.pdf',
        'hostile/03_wikipedia.pdf',
        'hostile/06_un_report.pdf',
        'hostile/07_usgs_map.pdf',
        'hostile/08_patent.pdf',
        'hostile/01_arxiv_paper.pdf',
        'hostile/04_rfc.pdf',
        'hostile/05_ieee_sample.pdf',
        'hostile/09_bank_statement.pdf',
        'hostile/10_business_invoice.pdf',
    ]
    pool.set_total(len(targets))
    for pdf in targets:
        r = await pool.process(Path(pdf), Path('test_results'), skip_vectors=False)
    await pool.stop()

asyncio.run(test())
