import subprocess
import sys
from sqlalchemy import create_engine, Column, Integer, Float, String, Sequence, Date, extract
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import tkinter as tk
from tkinter import messagebox, ttk
import matplotlib.pyplot as plt
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import json

def install_requirements():
    try:
        print("Loading...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()
    try:
        Base = declarative_base()
        class Expense(Base):
            __tablename__ = 'expenses'
            id = Column(Integer, Sequence('expense_id_seq'), primary_key=True)
            amount = Column(Float)
            category = Column(String(50))
            date = Column(Date)
        class Income(Base):
            __tablename__ = 'income'
            id = Column(Integer, Sequence('income_id_seq'), primary_key=True)
            amount = Column(Float)
            frequency = Column(String(10)) # 'monthly' or 'yearly'
        engine = create_engine('sqlite:///finances.db')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
    except ModuleNotFoundError as e:
        print(f"Error: {e}. Please ensure all modules are installed.")
        sys.exit(1)

def save_expense(amount, category, month, year, day):
    try:
        expense_date = datetime(year, month, day)
        expense = Expense(amount=amount, category=category, date=expense_date)
        session.add(expense)
        session.commit()
    except SQLAlchemyError as e:
        messagebox.showerror("Database Error", str(e))

def save_income(amount, frequency):
    try:
        income = session.query(Income).first()
        if income:
            income.amount = amount
            income.frequency = frequency
        else:
            income = Income(amount=amount, frequency=frequency)
        session.add(income)
        session.commit()
    except SQLAlchemyError as e:
        messagebox.showerror("Database Error", str(e))

def get_income():
    try:
        income = session.query(Income).first()
        if income:
            if income.frequency == 'yearly':
                return income.amount / 12 # Convert yearly income to monthly
            return income.amount
        return None
    except SQLAlchemyError as e:
        messagebox.showerror("Database Error", str(e))
        return None

def calculate_taxes(income):
    # Federal tax brackets for 2023 (example)
    federal_tax_brackets = [
        (10275, 0.10),
        (41775, 0.12),
        (89075, 0.22),
        (170050, 0.24),
        (215950, 0.32),
        (539900, 0.35),
        (float('inf'), 0.37)
    ]
    
    federal_tax = 0
    remaining_income = income
    for bracket in federal_tax_brackets:
        if remaining_income > bracket[0]:
            federal_tax += bracket[0] * bracket[1]
            remaining_income -= bracket[0]
        else:
            federal_tax += remaining_income * bracket[1]
            break
    state_tax = income * 0.0307 # Pennsylvania state tax rate
    local_tax = income * 0.011 # Lancaster local tax rate
    total_tax = federal_tax + state_tax + local_tax
    return total_tax

def calculate_savings(selected_month, selected_year, view_type):
    try:
        income = get_income()
        
        if view_type == 'monthly':
            total_expenses = session.query(Expense).filter(extract('month', Expense.date) == selected_month, extract('year', Expense.date) == selected_year).all()
            total_expense_amount = sum(expense.amount for expense in total_expenses)
            after_tax_income = income - calculate_taxes(income)
            monthly_savings = after_tax_income - total_expense_amount
            
            # Prioritize expenses over savings
            living_expenses = total_expense_amount
            monthly_savings -= living_expenses
            
            emergency_fund_target = total_expense_amount * 6 / 12
            emergency_savings = max(0, min(monthly_savings, emergency_fund_target))
            monthly_savings -= emergency_savings
            
            retirement_savings = max(0, min(monthly_savings, 7500 / 12))
            monthly_savings -= retirement_savings
            
            stock_investment = max(0, min(monthly_savings, monthly_savings * 0.10))
            monthly_savings -= stock_investment
            
            # Ensure no negative values
            living_expenses = max(living_expenses, 0)
            emergency_savings = max(emergency_savings, 0)
            retirement_savings = max(retirement_savings, 0)
            stock_investment = max(stock_investment, 0)
            
            # Warn if expenses approach $1000 and savings drop below zero
            if total_expense_amount >= after_tax_income - 1000:
                messagebox.showwarning("Budget Warning", "You are $1000 away from going over your budget for the month.")
            
            if monthly_savings <= 0:
                messagebox.showwarning("Savings Warning", "Your savings have hit 0 or below. Consider saving instead of spending if necessary.")
            
            return income, monthly_savings, emergency_savings, retirement_savings, stock_investment, living_expenses, total_expenses, total_expense_amount, after_tax_income, None
        
        else:
            total_expenses = session.query(Expense).filter(extract('year', Expense.date) == selected_year).all()
            total_expense_amount = sum(expense.amount for expense in total_expenses)
            yearly_income = income * 12
            after_tax_income = yearly_income - calculate_taxes(yearly_income)
            yearly_savings = after_tax_income - total_expense_amount
            
            # Prioritize expenses over savings for the year
            living_expenses = total_expense_amount
            yearly_savings -= living_expenses
            
            emergency_fund_target = total_expense_amount * 6 / 12
            emergency_savings = max(0, min(yearly_savings, emergency_fund_target))
            yearly_savings -= emergency_savings
            
            retirement_savings = max(0, min(yearly_savings, 7500))
            yearly_savings -= retirement_savings
            
            stock_investment = max(0, min(yearly_savings, yearly_savings * 0.10))
            yearly_savings -= stock_investment
            
            # Ensure no negative values
            living_expenses = max(living_expenses, 0)
            emergency_savings = max(emergency_savings, 0)
            retirement_savings = max(retirement_savings, 0)
            stock_investment = max(stock_investment, 0)
            
            # Performance line
            performance_line = "You did well for the year!" if yearly_savings > 0 else "You should try better next year."
            
            return income, yearly_savings, emergency_savings, retirement_savings, stock_investment, living_expenses, total_expenses, total_expense_amount, after_tax_income, performance_line
    except SQLAlchemyError as e:
        messagebox.showerror("Database Error", str(e))
        return None, None, None, None, None, None, [], None, None, None

def plot_expenses(expenses, view_type):
    categories = {}
    for expense in expenses:
        if expense.category in categories:
            categories[expense.category] += expense.amount
        else:
            categories[expense.category] = expense.amount
    plt.figure(figsize=(10, 5))
    if view_type == 'monthly':
        bars = plt.bar(categories.keys(), categories.values())
        plt.title('Monthly Expenses by Category')
    else:
        yearly_categories = {category: amount for category, amount in categories.items()}
        bars = plt.bar(yearly_categories.keys(), yearly_categories.values())
        plt.title('Yearly Expenses by Category')
    plt.xlabel('Category')
    plt.ylabel('Amount')
    # Add annotations to the bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval, f'${yval:.2f}', ha='center', va='bottom')
    plt.show()

def add_expense():
    try:
        amount = float(amount_entry.get())
        category = category_var.get()
        if category == "Other":
            category = other_entry.get()
        month = months.index(month_var.get()) + 1
        year = int(year_var.get())
        day = datetime.now().day # Get the current day
        save_expense(amount, category, month, year, day)
        messagebox.showinfo("Expense Added", f"Added expense of ${amount:.2f} to category '{category}' for {month_var.get()} {year}.")
        amount_entry.delete(0, tk.END)
        other_entry.delete(0, tk.END)
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid number for the amount.")

def set_income():
    try:
        income = float(income_entry.get())
        frequency = frequency_var.get()
        save_income(income, frequency)
        messagebox.showinfo("Income Set", f"{frequency.capitalize()} income set to ${income:.2f}.")
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a valid number for income.")

def update_month_dropdown(*args):
    selected_year = int(year_var.get())
    current_year = datetime.now().year
    current_month = datetime.now().month
    previous_month = month_var.get()
    if selected_year == current_year:
        valid_months = months[:current_month]
    else:
        valid_months = months
    if previous_month in valid_months:
        month_var.set(previous_month)
    else:
        month_var.set(valid_months[0])
    month_dropdown['menu'].delete(0, 'end')
    for month in valid_months:
        month_dropdown['menu'].add_command(label=month, command=tk._setit(month_var, month))

def calculate_and_display():
    try:
        selected_month = months.index(month_var.get()) + 1
        selected_year = int(year_var.get())
        view_type = view_type_var.get()
        income, savings, emergency_savings, retirement_savings, stock_investment, living_expenses, total_expenses, total_expense_amount, after_tax_income, performance_line = calculate_savings(selected_month, selected_year, view_type)
        
        if savings is not None:
            if view_type == 'monthly':
                if savings <= 0:
                    amount_under = total_expense_amount - after_tax_income
                    messagebox.showwarning("Savings Warning", f"Your savings have hit 0 or below. You lost ${abs(amount_under):.2f}. Consider saving instead of spending if necessary.")
                else:
                    messagebox.showinfo("Savings", f"Monthly Income: ${income:.2f}\n"
                                                  f"Monthly Savings: ${savings:.2f}\n"
                                                  f"Emergency Savings: ${emergency_savings:.2f}\n"
                                                  f"Retirement Savings: ${retirement_savings:.2f}\n"
                                                  f"Stock Investment: ${stock_investment:.2f}\n"
                                                  f"Living Expenses: ${living_expenses:.2f}\n"
                                                  f"Total Expenses for {month_var.get()} {selected_year}: ${total_expense_amount:.2f}")
            else:
                if savings <= 0:
                    amount_under = total_expense_amount - after_tax_income
                    messagebox.showwarning("Savings Warning", f"Your savings have hit 0 or below. You lost ${abs(amount_under):.2f}. Consider saving instead of spending if necessary.")
                else:
                    messagebox.showinfo("Yearly Summary", f"Yearly Income: ${after_tax_income:.2f}\n"
                                                          f"Yearly Savings: ${savings:.2f}\n"
                                                          f"Emergency Savings: ${emergency_savings:.2f}\n"
                                                          f"Retirement Savings: ${retirement_savings:.2f}\n"
                                                          f"Stock Investment: ${stock_investment:.2f}\n"
                                                          f"Living Expenses: ${living_expenses:.2f}\n"
                                                          f"Total Expenses for the Year: ${total_expense_amount:.2f}\n"
                                                          f"{performance_line}")
            plot_expenses(total_expenses, view_type)
    except TypeError:
        messagebox.showerror("Income Error", "Please set your monthly or yearly income first.")

def update_edit_month_dropdown(*args):
    selected_year = int(year_var.get())
    current_year = datetime.now().year
    current_month = datetime.now().month
    previous_month = month_var.get()
    
    # Ensure January is always included
    if selected_year == current_year:
        valid_months = months[:current_month]
    else:
        valid_months = months
    
    if previous_month in valid_months:
        month_var.set(previous_month)
    else:
        month_var.set(valid_months[0])
    
    menu = month_dropdown["menu"]
    menu.delete(0, "end")
    for month in valid_months:
        menu.add_command(label=month, command=tk._setit(month_var, month))

def open_edit_window():
    engine = create_engine('sqlite:///finances.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    def load_expenses():
        selected_month = months.index(edit_month_var.get()) + 1
        selected_year = int(edit_year_var.get())
        expenses = session.query(Expense).filter(extract('month', Expense.date) == selected_month, extract('year', Expense.date) == selected_year).all()
        expense_listbox.delete(0, tk.END)
        for expense in expenses:
            expense_listbox.insert(tk.END, f"{expense.id}: {expense.category} - ${expense.amount:.2f} on {expense.date.strftime('%Y-%m-%d')}")
    
    def edit_expense():
        try:
            selected_expense = expense_listbox.get(expense_listbox.curselection())
            expense_id = int(selected_expense.split(":")[0])
            new_amount = float(new_amount_entry.get())
            expense = session.query(Expense).filter(Expense.id == expense_id).first()
            expense.amount = new_amount
            session.commit()
            messagebox.showinfo("Expense Edited", f"Expense ID {expense_id} updated to ${new_amount:.2f}.")
            load_expenses()
        except (ValueError, IndexError):
            messagebox.showerror("Selection Error", "Please select an expense and enter a valid amount.")
    
    def delete_expense():
        try:
            selected_expense = expense_listbox.get(expense_listbox.curselection())
            expense_id = int(selected_expense.split(":")[0])
            expense = session.query(Expense).filter(Expense.id == expense_id).first()
            session.delete(expense)
            session.commit()
            messagebox.showinfo("Expense Deleted", f"Expense ID {expense_id} deleted.")
            load_expenses()
        except IndexError:
            messagebox.showerror("Selection Error", "Please select an expense to delete.")
    
    def save_edit_settings():
        settings = {
            "edit_month": edit_month_var.get(),
            "edit_year": edit_year_var.get()
        }
        with open("edit_settings.json", "w") as settings_file:
            json.dump(settings, settings_file)
    
    def load_edit_settings():
        try:
            with open("edit_settings.json", "r") as settings_file:
                settings = json.load(settings_file)
            edit_month_var.set(settings.get("edit_month", datetime.now().strftime('%B')))
            edit_year_var.set(settings.get("edit_year", str(datetime.now().year)))
        except FileNotFoundError:
            edit_month_var.set(datetime.now().strftime('%B'))
            edit_year_var.set(str(datetime.now().year))
    
    def update_edit_month_dropdown(*args):
        selected_year = int(edit_year_var.get())
        current_year = datetime.now().year
        current_month = datetime.now().month
        previous_month = edit_month_var.get()
        
        # Ensure January is always included
        if selected_year == current_year:
            valid_months = months[:current_month]
        else:
            valid_months = months
        
        if previous_month in valid_months:
            edit_month_var.set(previous_month)
        else:
            edit_month_var.set(valid_months[0])
        
        menu = edit_month_dropdown["menu"]
        menu.delete(0, "end")
        for month in valid_months:
            menu.add_command(label=month, command=tk._setit(edit_month_var, month))
    
    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Expenses")
    edit_window.transient(root) # Make the edit window a child of the main window
    edit_window.grab_set() # Make the edit window modal
    
    ttk.Label(edit_window, text="Select Month:").grid(row=0, column=0, padx=10, pady=5)
    edit_month_var = tk.StringVar(value=datetime.now().strftime('%B'))
    edit_month_dropdown = ttk.OptionMenu(edit_window, edit_month_var, *months)
    edit_month_dropdown.grid(row=0, column=1, padx=10, pady=5)
    
    ttk.Label(edit_window, text="Select Year:").grid(row=1, column=0, padx=10, pady=5)
    edit_year_var = tk.StringVar(value=str(datetime.now().year))
    edit_year_dropdown = ttk.OptionMenu(edit_window, edit_year_var, *years)
    edit_year_dropdown.grid(row=1, column=1, padx=10, pady=5)
    
    # Add trace to update month dropdown dynamically
    edit_year_var.trace('w', update_edit_month_dropdown)
    
    ttk.Button(edit_window, text="Load Expenses", command=load_expenses).grid(row=2, column=0, columnspan=2, pady=10)
    ttk.Label(edit_window, text="Expenses:").grid(row=3, column=0, columnspan=2)
    expense_listbox = tk.Listbox(edit_window, width=50)
    expense_listbox.grid(row=4, column=0, columnspan=2)
    
    ttk.Label(edit_window, text="New Amount:").grid(row=5, column=0)
    new_amount_entry = ttk.Entry(edit_window)
    new_amount_entry.grid(row=5, column=1)
    ttk.Button(edit_window, text="Edit Expense", command=edit_expense).grid(row=6, column=0)
    ttk.Button(edit_window, text="Delete Expense", command=delete_expense).grid(row=6, column=1)
    
    load_edit_settings()
    update_edit_month_dropdown()
    edit_window.protocol("WM_DELETE_WINDOW", lambda: [save_edit_settings(), edit_window.destroy()])

root = tk.Tk()
root.title("Savings and Expense Tracker")
style = ttk.Style()
style.configure("TLabel", padding=6, relief="flat", background="#f0f0f0")
style.configure("TButton", padding=6, relief="flat", background="#d9d9d9")
style.configure("TEntry", padding=6, relief="flat", background="#ffffff")

# Create frames for different sections
income_frame = ttk.Frame(root, padding="10 10 10 10")
income_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
expense_frame = ttk.Frame(root, padding="10 10 10 10")
expense_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
date_frame = ttk.Frame(root, padding="10 10 10 10")
date_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
button_frame = ttk.Frame(root, padding="10 10 10 10")
button_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))

# Function to set the initial income amount as greyed-out text
def set_income_placeholder():
    income = get_income()
    if income is not None:
        if frequency_var.get() == 'yearly':
            income *= 12 # Convert monthly income to yearly
        income_entry.insert(0, f"${income:.2f}")
        income_entry.config(foreground='grey', state='readonly')

# Function to enable editing the income amount
def enable_income_edit():
    income_entry.config(state='normal', foreground='black')
    income_entry.delete(0, tk.END)

# Function to update the income placeholder based on the selected frequency
def update_income_placeholder(*args):
    income_entry.config(state='normal')
    income_entry.delete(0, tk.END)
    set_income_placeholder()

# Income section
ttk.Label(income_frame, text="Income Amount:").grid(row=0, column=0, padx=10, pady=5)
income_entry = ttk.Entry(income_frame)
income_entry.grid(row=0, column=1, padx=10, pady=5)
frequency_var = tk.StringVar(value='monthly')
ttk.Radiobutton(income_frame, text="Monthly", variable=frequency_var, value='monthly').grid(row=1, column=0, padx=10, pady=5)
ttk.Radiobutton(income_frame, text="Yearly", variable=frequency_var, value='yearly').grid(row=1, column=1, padx=10, pady=5)

# Add trace to update the income placeholder when the frequency changes
frequency_var.trace('w', update_income_placeholder)

# Sets the number as greyed-out text.
set_income_placeholder()

# Button to set the income amount
set_income_button = ttk.Button(income_frame, text="Set Income", command=set_income)
set_income_button.grid(row=0, column=2, padx=5)

# Button to enable editing the income amount
edit_income_button = ttk.Button(income_frame, text="Edit", command=enable_income_edit)
edit_income_button.grid(row=0, column=3, padx=5)

# Expense section
ttk.Label(expense_frame, text="Expense Category:").grid(row=0, column=0, padx=10, pady=5)
category_var = tk.StringVar(value='Rent')
common_expenses = ["Rent", "Utilities", "Groceries", "Transportation", "Insurance", "Healthcare", "Entertainment", "Dining Out", "Education", "Other"]

def update_category_dropdown():
    # Ensure "Rent" is always included in the dropdown options
    if "Rent" not in common_expenses:
        common_expenses.insert(0, "Rent")
    menu = category_dropdown["menu"]
    menu.delete(0, "end")
    for expense in common_expenses:
        menu.add_command(label=expense, command=tk._setit(category_var, expense))

category_dropdown = ttk.OptionMenu(expense_frame, category_var, *common_expenses)
category_dropdown.grid(row=0, column=1, padx=10, pady=5)
update_category_dropdown()

other_entry = ttk.Entry(expense_frame)
other_entry.grid(row=0, column=2, padx=10, pady=5)
ttk.Label(expense_frame, text="Expense Amount:").grid(row=1, column=0, padx=10, pady=5)
amount_entry = ttk.Entry(expense_frame)
amount_entry.grid(row=1, column=1, padx=10, pady=5)

# Date section
ttk.Label(date_frame, text="Month:").grid(row=0, column=0, padx=10, pady=5)
month_var = tk.StringVar(value=datetime.now().strftime('%B'))
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
month_dropdown = ttk.OptionMenu(date_frame, month_var, *months)
month_dropdown.grid(row=0, column=1, padx=10, pady=5)
ttk.Label(date_frame, text="Year:").grid(row=1, column=0, padx=10, pady=5)
year_var = tk.StringVar(value=str(datetime.now().year))
years = [str(year) for year in range(datetime.now().year - 20, datetime.now().year + 1)] # Allowing years further back than 2016
year_dropdown = ttk.OptionMenu(date_frame, year_var, *years)
year_dropdown.grid(row=1, column=1, padx=10, pady=5)
year_var.trace('w', update_month_dropdown)

# Buttons between Year and View Type
ttk.Button(date_frame, text="Add Expense", command=add_expense).grid(row=2, column=0, padx=42, pady=5)
ttk.Button(date_frame, text="Edit Expenses", command=open_edit_window).grid(row=2, column=1, padx=10, pady=5)

# View Type section
ttk.Label(date_frame, text="View Type:").grid(row=4, column=0, padx=10, pady=5)
view_type_var = tk.StringVar(value='monthly')
ttk.Radiobutton(date_frame, text="Monthly", variable=view_type_var, value='monthly').grid(row=4, column=1, padx=10, pady=5)
ttk.Radiobutton(date_frame, text="Yearly", variable=view_type_var, value='yearly').grid(row=4, column=2, padx=10, pady=5)

# Placeholder text for other_entry
def set_placeholder(event):
    if other_entry.get() == '':
        other_entry.insert(0, 'Specify if "Other"')
        other_entry.config(foreground='grey')

def clear_placeholder(event):
    if other_entry.get() == 'Specify if "Other"':
        other_entry.delete(0, tk.END)
        other_entry.config(foreground='black')

other_entry.insert(0, 'Specify if "Other"')
other_entry.config(foreground='grey')
other_entry.bind('<FocusIn>', clear_placeholder)
other_entry.bind('<FocusOut>', set_placeholder)

# Bottom Button
ttk.Button(button_frame, text="Calculate Savings", command=calculate_and_display).grid(row=0, column=0, padx=150, pady=10, sticky="ew")

# Configure the row and column weights to allow expansion
button_frame.columnconfigure(0, weight=1)
button_frame.columnconfigure(1, weight=1)
button_frame.columnconfigure(2, weight=1)
button_frame.rowconfigure(0, weight=1)

def load_settings():
    try:
        with open("settings.json", "r") as settings_file:
            settings = json.load(settings_file)
        month_var.set(settings.get("edit_month", datetime.now().strftime('%B')))
        year_var.set(settings.get("edit_year", str(datetime.now().year)))
        view_type_var.set(settings.get("view_type", "monthly"))
    except FileNotFoundError:
        month_var.set(datetime.now().strftime('%B'))
        year_var.set(str(datetime.now().year))

load_settings()

def save_settings():
    settings = {
        "month": month_var.get(),
        "year": year_var.get(),
        "view_type": view_type_var.get()
    }
    with open("settings.json", "w") as settings_file:
        json.dump(settings, settings_file)

root.protocol("WM_DELETE_WINDOW", lambda: [save_settings(), root.destroy()])
print("Completed")
root.mainloop()