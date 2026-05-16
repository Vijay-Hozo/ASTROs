import os
import codecs

tests_dir = r'c:\Users\Steve\Desktop\hackathon\ASTROs-backend\tests\xml'
os.makedirs(tests_dir, exist_ok=True)

# Namespace heavy
ns_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<ubl:Invoice xmlns:ubl="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
             xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
             xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:invoice_id>INV-NS-001</cbc:invoice_id>
  <cbc:issue_date>2026-05-15</cbc:issue_date>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName>
        <cbc:seller_name>Namespaced Seller</cbc:seller_name>
      </cac:PartyName>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cbc:taxable_amount>1000.00</cbc:taxable_amount>
</ubl:Invoice>'''
with open(os.path.join(tests_dir, 'invoice_namespace_heavy.xml'), 'w') as f:
    f.write(ns_xml)

# Large XML stress
items = '<item><description>Stress item</description><quantity>1</quantity><unit_price>10.00</unit_price><line_total>10.00</line_total></item>' * 1500
large_xml = f'''<?xml version="1.0"?>
<Invoice>
  <invoice_id>INV-LARGE</invoice_id>
  <seller_name>Big Corp</seller_name>
  <buyer_name>Small Buyer</buyer_name>
  <line_items>{items}</line_items>
</Invoice>'''
with open(os.path.join(tests_dir, 'invoice_large_stress.xml'), 'w') as f:
    f.write(large_xml)

# Encoding edge-case UTF-16
utf16_xml = '''<?xml version="1.0" encoding="UTF-16"?>
<Invoice>
  <invoice_id>INV-U16</invoice_id>
  <seller_name>अमेज़ॅन</seller_name>
  <buyer_name>😊😎</buyer_name>
</Invoice>'''
with codecs.open(os.path.join(tests_dir, 'invoice_encoding_utf16.xml'), 'w', 'utf-16') as f:
    f.write(utf16_xml)

# Malicious XXE
xxe_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<Invoice>
  <invoice_id>&xxe;</invoice_id>
  <issue_date>2026-05-15</issue_date>
</Invoice>'''
with open(os.path.join(tests_dir, 'invoice_xxe.xml'), 'w') as f:
    f.write(xxe_xml)

# Malicious Billion Laughs
laughs_xml = '''<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
 <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
 <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
 <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
]>
<Invoice>
  <invoice_id>&lol5;</invoice_id>
</Invoice>'''
with open(os.path.join(tests_dir, 'invoice_billion_laughs.xml'), 'w') as f:
    f.write(laughs_xml)
