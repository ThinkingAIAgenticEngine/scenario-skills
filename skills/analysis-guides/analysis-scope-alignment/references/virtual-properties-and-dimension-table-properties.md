# Virtual Properties and Dimension Table Properties

Similar to events, event properties and user properties can be automatically generated through data reporting, or created in the data management interface by configuring calculation rules or adding dimension tables.

In the Data Management - Event Properties and User Properties interface, you can view and manage properties created through these three methods. Properties created through reporting are classified as preset properties and custom properties; properties created through configuring rules are classified as virtual properties; and properties created through adding dimension tables are dimension table properties.

## 1. Creating Virtual Properties

If you have the following needs, you can create virtual properties in the user properties or event properties interface:

- Need to use secondary calculations on reported properties or tags to generate new properties, such as multi-property numerical operations, multi-property concatenation, logical formulas, etc.
- Need to convert the data type of properties or tags, such as splitting text into arrays, objects, converting numerical values to text, etc.
- For more scenarios, see [Best Practices for Creating Virtual Properties](./creating-virtual-properties-best-practices.md)

### Using SQL Function Templates to Configure Virtual Properties

In TE version 4.0, we launched commonly used function templates to help users create virtual properties more conveniently and quickly.

- Hover your mouse over the function name to see the function's name, usage description, and example use cases.
- Click the "Insert" button, and the example will be successfully referenced into the edit box for users to perform secondary editing.
- You can freely copy and reference other event properties, user properties, or user tags to use with functions, creating virtual properties more flexibly.

**When configuring virtual property rules (see diagram below):**

- Cannot use created virtual properties to secondary-create virtual properties;
- Cannot use dimension table properties generated from virtual properties associated with data tables;
- Cannot use user tags whose analysis subject is a virtual property;

The configured rules must pass debugging before they can be saved. During debugging, the system will infer the property's data type based on the rule calculation results. If you need to force convert the rule's data type, you can manually adjust it, and need to debug again after adjustment.

Custom virtual event properties and their association with events can be set to automatic matching, where the system will infer the events that can be associated based on the virtual property rules. Users can also specify events to create association relationships.

## 2. Creating Dimension Table Properties

If you have the following needs, you can create dimension table properties in the user properties or event properties interface:

- Add readable display names for reported key-type properties (such as item ID), such as item name;
- Add more business information for reported key-type properties, such as item category, item price, etc.

You can add existing data tables as dimension tables for properties, or create new data tables as dimension tables. After adding as a dimension table, dimension table properties will be automatically generated based on non-primary key fields in that table. Dimension table properties can be used as event properties and user properties in analysis.

**The following properties cannot add dimension tables for themselves:**

- If the property's creation rule contains virtual properties and their sub-properties generated from dimension table properties, it cannot add a dimension table;
- If the event virtual property's creation rule contains user properties or user tags, it cannot add a dimension table;

**Different data types of properties have different requirements for dimension tables, as follows:**

| Property Data Type | Adding Dimension Table Notes |
|-------------------|------------------------------|
| Text, Number, Boolean | Can add dimension table, table primary key data type must be the same as the property. |
| Time | Can add dimension table, table primary key data type must be text, and time format must be specified. |
| List | Can add dimension table, table primary key data type must be text. |
| Object, Object Group | Cannot add dimension table properties. Object sub-properties can add dimension tables. |

Generally, the system automatically creates dimension table properties for fields in the dimension table (except the primary key). However, for dimension tables of list-type properties, only text-type fields in the table will create corresponding dimension table properties.