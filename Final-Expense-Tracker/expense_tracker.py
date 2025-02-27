import subprocess
import sys

def install_requirements():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()
    try:
        from sqlalchemy import create_engine, Column, Integer, Float, String, Sequence, Date, extract
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker
        import tkinter as tk
        from tkinter import messagebox
        import matplotlib.pyplot as plt
        from datetime import datetime
        from sqlalchemy.exc import SQLAlchemyError
    except ModuleNotFoundError as e:
        print(f"Error: {e}. Please ensure all modules are installed.")
        sys.exit(1)

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
        frequency = Column(String(10))  # 'monthly' or 'yearly'

    engine = create_engine('sqlite:///finances.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def save_expense(amount, category, month, year):
        try:
            expense_date = datetime(year, month, 1)
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
                    return income.amount / 12  # Convert yearly income to monthly
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

        state_tax = income * 0.0307  # Pennsylvania state tax rate
        local_tax = income * 0.011  # Lancaster local tax rate

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
            else:
                total_expenses = session.query(Expense).filter(extract('year', Expense.date) == selected_year).all()
                total_expense_amount = sum(expense.amount for expense in total_expenses)
                yearly_income = income * 12
                after_tax_income = yearly_income - calculate_taxes(yearly_income)
                monthly_savings = after_tax_income / 12 - total_expense_amount / 12

            # Emergency fund calculation (6 months of expenses)
            emergency_fund_target = total_expense_amount * 6 / 12
            emergency_savings = min(monthly_savings * 0.20, emergency_fund_target)

            # Ensure emergency savings are prioritized
            remaining_savings = monthly_savings - emergency_savings

            # IRA/401k contributions (up to $7,500/year for IRA, $22,500/year for 401k in 2023)
            retirement_savings = min(remaining_savings * 0.15, 7500 / 12)
            remaining_savings -= retirement_savings

            # Remaining savings for living and optional stock investment
            stock_investment = remaining_savings * 0.10
            living_expenses = remaining_savings - stock_investment

            return income, monthly_savings, emergency_savings, retirement_savings, stock_investment, living_expenses, total_expenses, total_expense_amount, after_tax_income
        except SQLAlchemyError as e:
            messagebox.showerror("Database Error", str(e))
            return None, None, None, None, None, None, [], None, None

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
            save_expense(amount, category, month, year)
            messagebox.showinfo("Expense Added", f"Added expense of ${amount:.2f} to category '{category}' for {month_var.get()} {year}.")
            amount_entry.delete(0, tk.END)
            other_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid number for the amount.")

