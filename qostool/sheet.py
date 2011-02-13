#! /usr/bin/env python
# -*- coding: iso-8859-15 -*-
"""
sheet
"""

import os, sys


class Sheet:

    def __init__(self, column_count=0):
        self.column_count = column_count
        self.header_names = None
        self.lines = []
        self.repr_lines = []
        self.sort_field_num = 0
        self.end_lines = []
        self.repr_end_lines = []


    def header(self, *field_names):
        self.column_count = len(field_names)
        self.header_names = field_names
        
    def line(self, *fields):
        if len(fields) != self.column_count:
            raise Exception("Bad column count")
        self.lines.append(fields)

    def end_line(self, *fields):
        if len(fields) != self.column_count:
            raise Exception("Bad column count")
        self.end_lines.append(fields)

        
    def sort_cmp(self, line1, line2):
        if line1[self.sort_field_num] < line2[self.sort_field_num]:
            return -1
        elif line1[self.sort_field_num] > line2[self.sort_field_num]:
            return 1
        else:
            return 0
    
    def limit(self, num_lines, order_desc=False):
        if order_desc:
            self.lines = self.lines[0:num_lines]
        else:
            if num_lines > len(self.lines):
                num_lines = len(self.lines)
            self.lines = self.lines[len(self.lines)-num_lines:]
    
    def sort(self, field_num):
        self.sort_field_num = field_num
        self.lines.sort(self.sort_cmp)
    
    def format(self, obj):
        if type(obj) == float:
            return "%.3f" % obj
        elif type(obj) == int:
            return "%d" % obj
        else:
            return str(obj)        
    
    def create_repr(self):
        self.repr_lines = []
        for line in self.lines:
            self.repr_lines.append([ self.format(x) for x in line ])
        self.repr_end_lines = []
        for line in self.end_lines:
            self.repr_end_lines.append([ self.format(x) for x in line ])
    
    def allocate_widths(self, columns):
        max_widths = [0]*self.column_count
        for line in self.repr_lines:
            for col_idx in range(self.column_count):
                max_widths[col_idx] = max(max_widths[col_idx], len(line[col_idx])+2)
        for line in self.repr_end_lines:
            for col_idx in range(self.column_count):
                max_widths[col_idx] = max(max_widths[col_idx], len(line[col_idx])+2)
                
        if sum(max_widths) < columns:
            return max_widths
        else:
            # TODO: scarce alloc !
            return max_widths
    
    def show(self, columns=0, out=sys.stdout):
        if columns == 0:
            try:
                columns = int(os.getenv("COLUMNS"))
            except:
                columns = 80

        self.create_repr()        
        widths = self.allocate_widths(columns)

        # show headers
        column_range = range(self.column_count)
        for i in column_range:
            name = self.header_names[i]
            out.write(" %s " % name)
                        
            out.write( ' '*(widths[i] - len(name) - 2))
            out.write('|')
            
        out.write("\n")
        
        sep_line = ""
        for i in column_range:
            if i == self.sort_field_num:
                sep_line += 'v'*widths[i]
            else:
                sep_line += '-'*widths[i]

            sep_line += '+'
        
        print sep_line
        
        for line in self.repr_lines:
            for i in column_range:
                value = line[i]
                out.write(' ')
                out.write(value)
                out.write(' '*(widths[i]-len(value)-1))
                out.write('|')
            out.write('\n')
            
        print sep_line

        
        for line in self.repr_end_lines:
            for i in column_range:
                value = line[i]
                out.write(' ')
                out.write(value)
                out.write(' '*(widths[i]-len(value)-1))
                out.write('|')
            out.write('\n')            
            

        
