import os, sys, re

def show_exception_and_exit(exc_type, exc_value, tb):
	import traceback
	
	traceback.print_exception(exc_type, exc_value, tb)
	sys.exit(-1)

def macroize_name(name):
	return re.sub(r"[^A-Za-z0-9_]", '_', name).upper()

class TextProcessError(Exception):

	def __init__(self, fileName, lineNumber, errDesc):
		self.fileName   = fileName
		self.lineNumber = lineNumber
		self.errDesc    = errDesc

class TextEntry:

	def __init__(self, text, stringId, definition = None):
		self.text       = text
		self.stringId   = stringId
		self.definition = definition

	def get_unique_identifier(self):
		return self.definition if self.definition else "{:03X}".format(self.stringId)

def generate_text_entries(lines):
	"""takes a compiled file and returns a list of individual text entries"""

	result = []

	currentStringId = 0

	currentText = None
	currentDefinition = None

	for (fileName, iLine, line) in lines:
		l = line.strip()

		if currentText == None: # no current text, reading entry header
			if l == "":
				next # Skip empty lines

			else:
				match = re.match(r"^#\s*([0x[0-9a-fA-F]+|#)\s*(\w+)?$", l, re.M | re.I)

				if not match:
					raise TextProcessError(fileName, iLine+1, "expected entry header!")

				if match.group(1) == '#': # if no ID given, use the previous one + 1
					currentStringId = currentStringId+1

				else:
					currentStringId = int(match.group(1), base = 0)
				
				currentDefinition = match.group(2)
				currentText = ""

		else:
			currentText += line + "\n"

			if l[-3:] == "[X]": # Line ends in [X] (end of text entry)
				result.append(TextEntry(currentText, currentStringId, currentDefinition))

				currentText       = None
				currentDefinition = None

	return result

def preprocess(fileName, includeDepth = 0):
	if includeDepth > 500:
		print("Warning: #include depth exceeds 500. Check for circular inclusion.\nCurrent file: " + fileName)
		return None

	with open(fileName, 'r') as f:
		for iLine, line in enumerate(f.readlines()):
			m = re.match(r"^#include\s+(.+)", line.strip(), re.M | re.I)

			if m:
				includee = m.group(1).strip()

				if (includee[0] == '"'):
					includee = includee.strip('"')

				dirpath = os.path.dirname(fileName)

				if len(dirpath) > 0:
					includee = os.path.join(dirpath, includee)

				for otherLine in preprocess(includee, includeDepth+1):
					yield otherLine

			else:
				yield (fileName, iLine, line)

def generate_definitions_lines(name, textEntries):
	yield "// Text Definitions generated by text-process\n"
	yield "// Do not edit!\n\n"

	yield "#ifndef TEXT_DEFINITIONS_{}\n".format(name)
	yield "#define TEXT_DEFINITIONS_{}\n\n".format(name)

	for entry in textEntries:
		if entry.definition:
			yield "#define {} ${:03X}\n".format(entry.definition, entry.stringId)

	yield "\n#endif // TEXT_DEFINITIONS_{}\n".format(name)

def main():
	sys.excepthook = show_exception_and_exit

	print(f"WARNING: This tool (text-process.py) is deprecated in favor of text-process-classic.py.")

	if len(sys.argv) != 4:
		sys.exit("Usage: (python3) {} <input> <install output> <definition output>".format(sys.argv[0]))

	inputPath     = sys.argv[1]
	outputPath    = sys.argv[2]
	outputDefPath = sys.argv[3]

	if not os.path.exists(inputPath):
		sys.exit("`{}` doesn't exist".format(inputPath))

	(cwd, inputFile) = os.path.split(inputPath)
	inputName = os.path.splitext(inputFile)[0]

	# Read the entries

	entryList = []

	macroizedInputName = macroize_name(inputPath)

	try:
		usedStringIds   = []
		usedDefinitions = []

		for entry in generate_text_entries(preprocess(inputPath)): # create separate files for each text entry
			if entry.stringId in usedStringIds:
				print("WARNING: Duplicate entry for text Id {:03X}! (ignoring)".format(entry.stringId))

				if entry.definition:
					print("NOTE: Second entry was defined as `{}`".format(entry.definition))

				continue

			usedStringIds.append(entry.stringId)

			if entry.definition and (entry.definition in usedDefinitions):
				print("WARNING: Duplicate entry definition {}! (ignoring)".format(entry.definition))

				continue

			entryList.append(entry)

	except TextProcessError as e:
		sys.exit("ERROR: in file `{}`, line {}:\n  {}".format(e.fileName, e.lineNumber, e.errDesc))

	# Write the entries

	# Doing it late to avoid leaving the generated files half done
	# (Otherwise make will consider them updated even if they're bad)

	textFolder = os.path.join(cwd, ".TextEntries")

	if not os.path.exists(textFolder):
		os.mkdir(textFolder)

	with open(outputPath, 'w') as f:
		f.write("// Text Data Installer generated by text-process\n")
		f.write("// Do not edit!\n\n")

		f.write("#ifndef TEXT_INSTALLER_{}\n".format(macroizedInputName))
		f.write("#define TEXT_INSTALLER_{}\n\n".format(macroizedInputName))

		f.write("#include \"Tools/Tool Helpers.txt\"\n")
		f.write("#include \"{}\"\n\n".format(os.path.relpath(outputDefPath, os.path.dirname(outputPath))))

		f.write("{\n\n")

		for entry in entryList:
			textFileName  = os.path.join(textFolder, "{}{}.fetxt".format(inputName, entry.get_unique_identifier()))
			textDataLabel = "__TEXTPROCESS{:03X}".format(entry.stringId)

			# Write include

			f.write("{}:\n".format(textDataLabel))
			f.write('#incbin "{}.dmp"\n'.format(os.path.relpath(textFileName, os.path.dirname(outputPath))))
			f.write("setText(${:X}, {})\n\n".format(entry.stringId, textDataLabel))

			# Check if file exists with the same content
			# This is to prevent make to rebuild files that depend on this
			# As it would not have changed

			if os.path.exists(textFileName):
				with open(textFileName, 'r') as tf:
					if str(tf.read()) == entry.text:
						continue

			# Write data

			with open(textFileName, 'w') as tf:
				tf.write(entry.text)

		f.write("}\n\n")

		f.write("#endif // TEXT_INSTALLER_{}\n".format(macroizedInputName))

	with open(outputDefPath, 'w') as f:
		f.writelines(generate_definitions_lines(macroizedInputName, entryList))

if __name__ == '__main__':
	main()
