#!/usr/bin/env python3
"""Numerical acceptance cases. Run from any working directory."""
import copy, csv, io, json, random, subprocess, sys, tempfile, unittest
from decimal import Decimal, localcontext
from pathlib import Path
from analyze_sales import analyze, number
ROOT=Path(__file__).resolve().parents[1]
CONTRACT=json.loads((ROOT/'assets/contract.example.json').read_text())
SAMPLE=(ROOT/'assets/sales.example.csv').read_text()

class Acceptance(unittest.TestCase):
    def case(self,text=SAMPLE,contract=None):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'sales.csv').write_text(text,encoding='utf-8')
            (p/'contract.json').write_text(json.dumps(contract or CONTRACT),encoding='utf-8')
            with localcontext() as ctx:
                ctx.prec=60
                return analyze(p/'sales.csv',p/'contract.json')

    def test_mix_oracle(self):
        r=self.case();e=r['currencies']['USD'];b=e['profit_bridge']
        self.assertEqual(r['status'],'computed')
        self.assertEqual(e['prior']['revenue'],9000)
        self.assertEqual(e['current']['revenue'],10000)
        self.assertEqual(e['prior']['gross_profit'],4200)
        self.assertEqual(e['current']['gross_profit'],3200)
        self.assertEqual(e['current']['margin'],Decimal('0.32'))
        self.assertEqual(b['components']['volume'],2520)
        self.assertEqual(b['components']['mix'],-3520)
        self.assertEqual(b['components']['price'],0)
        self.assertEqual(b['components']['unit_cost'],0)
        self.assertTrue(b['reconciled'])
        self.assertEqual(b['residual'],0)

    def test_price_cost_oracle(self):
        text='line_id,date,product,quantity,revenue,cost,currency\n1,2026-01-01,A,10,100,60,USD\n2,2026-02-01,A,12,144,84,USD\n'
        b=self.case(text)['currencies']['USD']['profit_bridge']['components']
        self.assertEqual(b['volume'],8)
        self.assertEqual(b['price'],24)
        self.assertEqual(b['unit_cost'],-12)

    def test_bad_inputs_block(self):
        for replacement in ('NaN','1,23','','USD 100','Infinity'):
            with self.subTest(value=replacement):
                r=self.case(SAMPLE.replace('8000,4000','"'+replacement+'",4000'))
                self.assertEqual(r['status'],'blocked')
                self.assertFalse(r['currencies'])

    def test_duplicate_key_blocks(self):
        self.assertEqual(self.case(SAMPLE.replace('C1,','P1,'))['status'],'blocked')

    def test_currencies_not_combined(self):
        r=self.case(SAMPLE.replace('P2,2026-01-15,Basic,20,1000,800,USD','P2,2026-01-15,Basic,20,1000,800,EUR'))
        self.assertEqual(r['status'],'needs_review')
        self.assertIsNone(r['currencies']['EUR']['absolute_change'])
        self.assertIsNone(r['currencies']['EUR']['growth'])
        self.assertEqual(r['currencies']['USD']['prior']['revenue'],8000)

    def test_missing_units_suppress_bridge(self):
        c=copy.deepcopy(CONTRACT);c['quantity_unit']=None
        e=self.case(contract=c)['currencies']['USD']
        self.assertIsNone(e['profit_bridge'])
        self.assertIsNone(e['prior']['quantity'])

    def test_locale(self):
        self.assertEqual(number('1.234,50',',','.'),Decimal('1234.50'))
        self.assertEqual(number('(1,234.50)','.',','),Decimal('-1234.50'))
        with self.assertRaises(ValueError):number('12,34.50','.',',')

    def test_output_preserves_input(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);src=p/'s.csv';cfg=p/'c.json'
            src.write_text(SAMPLE);cfg.write_text(json.dumps(CONTRACT))
            r=subprocess.run([sys.executable,str(ROOT/'scripts/analyze_sales.py'),'--input',str(src),'--config',str(cfg),'--out',str(src)],capture_output=True)
            self.assertEqual(r.returncode,2)
            self.assertEqual(src.read_text(),SAMPLE)

    def test_weighted_margin(self):
        e=self.case()['currencies']['USD']
        with localcontext() as ctx:
            ctx.prec=60
            self.assertEqual(e['prior']['margin'],Decimal(4200)/9000)
        self.assertNotEqual(e['prior']['margin'],Decimal('0.35'))

    def test_identical_rows_retained_without_key(self):
        c=copy.deepcopy(CONTRACT);del c['columns']['unique_id']
        r=self.case(SAMPLE+SAMPLE.splitlines()[1]+'\n',c)
        self.assertEqual(r['currencies']['USD']['prior']['revenue'],17000)
        self.assertIn('identical_row_retained',[x['code'] for x in r['flags']])

    def test_invalid_calendar(self):
        self.assertEqual(self.case(SAMPLE.replace('2026-02-10','2026-02-30'))['status'],'blocked')

    def test_overlapping_periods(self):
        c=copy.deepcopy(CONTRACT);c['periods']['current']['start']='2026-01-31'
        with self.assertRaises(ValueError):self.case(contract=c)

    def test_nonpositive_baselines(self):
        for old in ('0','-100'):
            text=f'line_id,date,product,quantity,revenue,cost,currency\n1,2026-01-01,A,1,{old},0,USD\n2,2026-02-01,A,1,100,50,USD\n'
            e=self.case(text)['currencies']['USD']
            self.assertIsNone(e['growth']['revenue'])
            self.assertIsNone(e['prior']['margin'])

    def test_entrants_exits_returns(self):
        text=('line_id,date,product,quantity,revenue,cost,currency\n'
              '1,2026-01-01,Old,2,100,60,USD\n2,2026-01-02,Return,0,0,0,USD\n'
              '3,2026-02-01,New,3,200,120,USD\n4,2026-02-02,Return,-1,-50,-30,USD\n')
        b=self.case(text)['currencies']['USD']['profit_bridge']
        self.assertEqual(b['components']['entrants'],80)
        self.assertEqual(b['components']['exits'],-40)
        self.assertEqual(b['components']['other_adjustments'],-20)
        self.assertEqual(b['gross_profit_change'],20)
        self.assertTrue(b['reconciled'])

    def test_randomized_bridge(self):
        rng=random.Random(1706)
        for _ in range(50):
            buffer=io.StringIO();w=csv.writer(buffer)
            w.writerow(['line_id','date','product','quantity','revenue','cost','currency'])
            for month in (1,2):
                for product in range(8):
                    q,p,c=rng.randint(1,150),rng.randint(1,300),rng.randint(0,350)
                    w.writerow([f'{month}-{product}',f'2026-0{month}-01',f'P{product}',q,q*p,q*c,'USD'])
            self.assertTrue(self.case(buffer.getvalue())['currencies']['USD']['profit_bridge']['reconciled'])

    def test_empty_period(self):
        self.assertEqual(self.case('\n'.join(SAMPLE.splitlines()[:3])+'\n')['status'],'blocked')

if __name__=='__main__':unittest.main(verbosity=2)

