# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from itertools import cycle
import random

from model_mommy import mommy
from model_mommy.recipe import Recipe, seq, foreign_key

from ..models import LineItemType

line_item_type = Recipe(LineItemType, 
	text=seq('Text '),
	amount_dec=lambda:random.randint(1,400),
 )
