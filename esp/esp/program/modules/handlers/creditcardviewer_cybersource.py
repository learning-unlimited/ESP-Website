
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.datatree.models import GetNode
from esp.web.util        import render_to_response
from esp.money.models    import PaymentType, Transaction
from datetime            import datetime        
from esp.db.models       import Q
from esp.users.models    import User, ESPUser
#from esp.money.models    import RegisterLineItem, UnRegisterLineItem, PayForLineItems, LineItem, LineItemType
from esp.accounting_core.models import LineItemType, EmptyTransactionException, Balance
from esp.accounting_docs.models import Document
from esp.middleware      import ESPError

class CreditCardViewer_Cybersource(ProgramModuleObj):
    def extensions(self):
        return [('creditCardInfo', module_ext.CreditCardModuleInfo)]

    @needs_admin
    def viewpay_cybersource(self, request, tl, one, two, module, extra, prog):
        student_list = prog.students()

        payment_table = [ (student, student.document_set.filter(anchor=self.program_anchor_cached())) for student in student_list ]

        context = { 'payment_table': payment_table }
        
        return render_to_response(self.baseDir() + 'viewpay_cybersource.html', request, (prog, tl), context)
