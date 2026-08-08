# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from crm.api.exchange_rate import get_exchange_rate


class CRMOrganization(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.Link | None
		annual_revenue: DF.Currency
		currency: DF.Link | None
		exchange_rate: DF.Float
		industry: DF.Link | None
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		organization_logo: DF.AttachImage | None
		organization_name: DF.Data | None
		territory: DF.Link | None
		website: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.update_exchange_rate()

	def update_exchange_rate(self):
		if self.has_value_changed("currency") or not self.exchange_rate:
			system_currency = frappe.db.get_single_value("FCRM Settings", "currency") or "USD"
			exchange_rate = 1
			if self.currency and self.currency != system_currency:
				exchange_rate = get_exchange_rate(self.currency, system_currency)

			self.db_set("exchange_rate", exchange_rate)

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Student Name",
				"type": "Data",
				"key": "organization_name",
				"width": "12rem",
			},
			{
				"label": "Application ID",
				"type": "Data",
				"key": "application_id",
				"width": "10rem",
			},
			{
				"label": "Email",
				"type": "Data",
				"key": "student_email",
				"width": "14rem",
			},
			{
				"label": "Phone",
				"type": "Data",
				"key": "student_phone",
				"width": "10rem",
			},
			{
				"label": "Program",
				"type": "Data",
				"key": "program",
				"width": "10rem",
			},
			{
				"label": "University",
				"type": "Data",
				"key": "university",
				"width": "10rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"organization_name",
			"organization_logo",
			"application_id",
			"student_email",
			"student_phone",
			"program",
			"university",
			"modified",
		]
		return {"columns": columns, "rows": rows}
