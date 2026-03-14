#!/usr/bin/env python3
"""
German Vocabulary Cleaner
Removes unwanted lines (underscores) from copied German vocabulary
Also removes spaces between articles and nouns (die Trauer → dieTrauer)
Uses automatic translation with googletrans
Provides English translations and creates Excel-ready format
"""

def get_translation(german_text):
    """
    Get English translation for German text using googletrans
    """
    try:
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(german_text, src='de', dest='en')
        return result.text
    except ImportError:
        print("❌ googletrans not installed. Install with: pip install googletrans==4.0.0rc1")
        return "[INSTALL GOOGLETRANS]"
    except Exception as e:
        print(f"⚠️  Translation error for '{german_text}': {e}")
        return "[TRANSLATION ERROR]"

def remove_article_spaces(text):
    """
    Remove spaces between German articles (der, die, das) and nouns
    """
    articles = ['der ', 'die ', 'das ']
    
    for article in articles:
        if text.startswith(article):
            # Remove the space after the article
            return article.rstrip() + text[len(article):]
    
    return text

def create_excel_format(input_file, output_file):
    """
    Process raw German vocab and create Excel-ready format with translations
    Combines cleaning and translation in one step
    """
    with open(input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    excel_lines = []
    processed_count = 0
    
    # Add header row
    excel_lines.append("German\tEnglish\n")
    
    print("🔄 Processing and translating vocabulary...")
    
    for i, line in enumerate(lines, 1):
        stripped_line = line.strip()
        
        # Skip empty lines
        if not stripped_line:
            continue
            
        # Remove underscores from the end of the line
        if '_' in stripped_line:
            vocab_part = stripped_line.split('_')[0].strip()
            if not vocab_part:  # Skip if nothing left after removing underscores
                continue
        else:
            vocab_part = stripped_line
            
        # Remove spaces between articles and nouns
        vocab_part = remove_article_spaces(vocab_part)
        
        # Get English translation using automatic translation
        english_translation = get_translation(vocab_part)
        
        # Create tab-separated format: German word + tab + English translation
        excel_lines.append(f"{vocab_part}\t{english_translation}\n")
        processed_count += 1
    
    with open(output_file, 'w', encoding='utf-8') as file:
        file.writelines(excel_lines)
    
    print(f"✅ Complete! {processed_count} words cleaned and translated.")
    return processed_count

def main():
    input_file = 'german_vocab_raw.txt'
    excel_file = 'german_vocab_excel.txt'
    
    print("🧹 Cleaning and translating German vocabulary...")
    print("   • Removing underscores")
    print("   • Joining articles with nouns (die Trauer → dieTrauer)")
    print("   • Auto-translating to English")
    print("   • Creating Excel-ready format")
    
    try:
        # Process raw vocab directly to Excel format
        vocab_count = create_excel_format(input_file, excel_file)
        
        print(f"✅ All done!")
        print(f"📚 Vocabulary words processed: {vocab_count}")
        print(f"📊 Excel-ready format saved to: {excel_file}")
        print(f"💡 Copy content from {excel_file} and paste into Excel!")
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find {input_file}")
        print("Make sure your raw vocabulary file exists!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
