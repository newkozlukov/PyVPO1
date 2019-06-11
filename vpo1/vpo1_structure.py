import itertools
import collections
import typing

import pandas as pd


class VPO1Error(Exception):
    pass

class VPO1Row:
    def __init__(self, cells):
        # consider, for `str`s:
        # cells = map(str.strip, cells)
        # cells = map(str.lower, cells)
        # plus multiple spaces, etc
        cells = list(cells)
        self.cells = cells
        self.atomic_to_full = [i if c is not None else None for i, c in enumerate(cells)]
        self.atomic_to_full[0] = 0
        self._n_cells = sum(map(lambda x: x is not None, self.atomic_to_full))
        for i, ref in enumerate(self.atomic_to_full):
            if ref is None:
                self.atomic_to_full[i] = self.atomic_to_full[i - 1]
        for ref in self.atomic_to_full:
            assert ref is not None
    @property
    def n_cells(self):
        return self._n_cells
    @property
    def n_atomic_cells(self):
        return len(self.cells)
    def clone(self):
        return VPO1Row(self.cells)
    def __getitem__(self, atomic_cell_id):
        cell_id = self.atomic_to_full[atomic_cell_id]
        return self.cells[cell_id]
    def __setitem__(self, atomic_cell_id, value):
        cell_id = self.atomic_to_full[atomic_cell_id]
        self.cells[cell_id] = value
    def __repr__(self):
        return repr(self.cells)
    
class VPO1SheetHeader:
    DESC = ['region', 'funded_by', 'time_involvement', 'name', 'units']
    DESC = dict(((x, i) for i, x in enumerate(DESC)))
    def __init__(self, rows: typing.List[VPO1Row], n_cols: int):
        
        if len(rows) < len(VPO1SheetHeader.DESC):
            raise VPO1Error(
                'Expected at least {} rows in the header (for the traits) got {}'
                .format(len(rows, len(VPO1SheetHeader.DESC)))
            )
        if not isinstance(rows[VPO1SheetHeader.DESC['units']][0], str):
            raise VPO1Error('Units of measurement misspecified')
        if not 'ОКЕИ' in rows[VPO1SheetHeader.DESC['units']][0]:
            raise VPO1Error('Units of measurement misspecified')
        
        
        TRANSFORMS = collections.defaultdict(lambda: (lambda x: x))
        # TRANSFORMS['units'] = lambda x: x.replace(STARTSWITH_UNITS, '')
        for field, i in VPO1SheetHeader.DESC.items():
            transform = TRANSFORMS[field]
            setattr(self, field, transform(rows[i][0]))
        
        def table_header_transform(x):
            if x is None:
                return ''
            return str(x)
        table_header_start = len(VPO1SheetHeader.DESC) + 1
        table_header = (
            (row[i] for row in rows[table_header_start:])
            for i in range(n_cols)
        )
        table_header = [' '.join(map(table_header_transform, col)) for col in table_header]
        self.table_header = table_header
        self.n_cols = n_cols
        
def vpo1_table(header: VPO1SheetHeader,
               rows: typing.List[VPO1Row]) -> pd.DataFrame:
    index = [row[0] for row in rows]
    cols = header.table_header[1: ]
    data = data=[[row[i] for i in range(1, header.n_cols)] for row in rows]
    df = pd.DataFrame(data=data,
                      index=index,
                      columns=cols)
    return df

class VPO1Sheet:
    def __init__(self, rows: typing.List[VPO1Row]):
        try:
            idx_col_numbers = next(i for i, x in enumerate(rows)
                                   if isinstance(x[0], float) and x[0] == 1)
        except StopIteration:
            raise VPO1Erro('Invalid sheet. You probably should just skip it.')
        n_cols = max(map(lambda r: r.n_cells, rows))
        self.header = VPO1SheetHeader(rows[:idx_col_numbers], n_cols)
        self.table = vpo1_table(self.header, rows[idx_col_numbers + 1: ])
        for field in VPO1SheetHeader.DESC:
            setattr(self, field, getattr(self.header, field))
    @staticmethod
    def try_yield_parsed(rows):
        try:
            yield VPO1Sheet(rows)
        except VPO1Error:
            pass

    
class VPO1:
    def __init__(self, sheets: typing.Dict[str, typing.List[VPO1Row]]):
        # sheets = map(lambda name, rows: zip([name], VPO1Sheet.try_yield_parsed(rows)), sheets.items())
        sheets = (list(zip([name], VPO1Sheet.try_yield_parsed(rows))) for name, rows in sheets.items())
        sheets = itertools.chain.from_iterable(sheets)
        sheets = list(sheets)
        self.names, self.sheets = [n for n, p in sheets], [p for n, p in sheets]
        if len(self.sheets) == 0:
            raise VPO1Error('No sheets could be parsed')
        page0 = self.sheets[0]
        self.region = page0.region
        self.time_involvement = page0.time_involvement
    @staticmethod
    def try_yield_parsed(sheets):
        try:
            yield VPO1(sheets)
        except VPO1Error:
            pass
