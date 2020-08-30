
import os, sys, re

INPUT_ENCODING = "sjis"
OUTPUT_ENCODING = "sjis"

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

	def get_pretty_identifier(self):
		if self.definition:
			return "{:03X} {}".format(self.stringId, self.definition)

		return "{:03X}".format(self.stringId)

class ParseFileError(Exception):

	def __init__(self, textEntry, errDesc):
		self.textEntry = textEntry
		self.errDesc   = errDesc

def generate_text_entries(lines, doTrace):
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

				if doTrace:
					print("TRACE: [generate_text_entries] read {}".format(result[-1].get_pretty_identifier()))

				currentText       = None
				currentDefinition = None

	return result

def preprocess(fileName, doTrace, includeDepth = 0):
	if includeDepth > 500:
		print("Warning: #include depth exceeds 500. Check for circular inclusion.\nCurrent file: " + fileName)
		return None

	if doTrace:
		print("TRACE: [preprocess] opening `{}`".format(fileName))

	with open(fileName, 'r', encoding=INPUT_ENCODING) as f:
		for iLine, line in enumerate(f.readlines()):
			m = re.match(r"^#include\s+(.+)", line.strip(), re.M | re.I)

			if m:
				includee = m.group(1).strip()

				if (includee[0] == '"'):
					includee = includee.strip('"')

				dirpath = os.path.dirname(fileName)

				if len(dirpath) > 0:
					includee = os.path.join(dirpath, includee)

				for otherLine in preprocess(includee, doTrace, includeDepth+1):
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

def generate_text_binary(parseFileExe, textEntry, sourceFile, targetFile):
	import subprocess as sp

	result = sp.run([parseFileExe, sourceFile, "--to-stdout"], stdout = sp.PIPE)

	if result.stdout[:6] == b"ERROR:":
		os.remove(sourceFile)
		raise ParseFileError(textEntry, result.stdout[6:].strip().decode("utf-8"))

	with open(targetFile, 'wb') as f:
		f.write(result.stdout)

def main(args):
	import argparse

	argParse = argparse.ArgumentParser()

	argParse.add_argument('input', help = 'input text file')
	argParse.add_argument('--installer', default = 'Install Text Data.event', help = 'name of the installer event file to produce')
	argParse.add_argument('--definitions', default = 'Text Definitions.event', help = 'name of the definitions event file to produce')
	argParse.add_argument('--parser-exe', default = None, help = 'name/path of the parser executable')
	argParse.add_argument('--depends', default = None, nargs='*', help = 'files that text depends on (typically ParseDefinitions.txt)')
	argParse.add_argument('--force-refresh', action = 'store_true', help = 'pass to forcefully refresh generated files')
	argParse.add_argument('--verbose', action = 'store_true', help = 'print processing details to stdout')

	arguments = argParse.parse_args(args)

	inputPath     = arguments.input
	outputPath    = arguments.installer
	outputDefPath = arguments.definitions
	parserExePath = arguments.parser_exe
	forceRefresh  = True if arguments.force_refresh else False
	verbose       = True if arguments.verbose else False

	timeThreshold = 0.0

	if not arguments.depends:
		# Hacky thing to automatically depend on ParseDefinitions.txt if the parser is ParseFile

		if parserExePath and "ParseFile" in parserExePath:
			if os.path.exists("ParseDefinitions.txt"):
				arguments.depends = ["ParseDefinitions.txt"]

	if arguments.depends:
		timeThreshold = max([os.path.getmtime(filename) for filename in arguments.depends])

	sys.excepthook = show_exception_and_exit

	if not os.path.exists(inputPath):
		sys.exit("`{}` doesn't exist".format(inputPath))

	(cwd, inputFile) = os.path.split(inputPath)
	inputName = os.path.splitext(inputFile)[0]

	# Read the entries

	if verbose:
		print("TRACE: [global] start reading input")

	entryList = []

	macroizedInputName = macroize_name(inputPath)

	hasParser = parserExePath and os.path.exists(parserExePath)

	try:
		usedStringIds   = []
		usedDefinitions = []

		for entry in generate_text_entries(preprocess(inputPath, verbose), verbose): # create separate files for each text entry
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

	if verbose:
		print("TRACE: [global] start generating output")

	if not os.path.exists(textFolder):
		os.mkdir(textFolder)

	try:
		with open(outputPath, 'w') as f:
			f.write("// Text Data Installer generated by text-process\n")
			f.write("// Do not edit! (or do but it won't be of any use)\n\n")

			f.write("#ifndef TEXT_INSTALLER_{}\n".format(macroizedInputName))
			f.write("#define TEXT_INSTALLER_{}\n\n".format(macroizedInputName))

			f.write("#include \"Tools/Tool Helpers.txt\"\n")
			f.write("#include \"{}\"\n\n".format(os.path.relpath(outputDefPath, os.path.dirname(outputPath))))

			f.write("{\n\n")

			for entry in entryList:
				textFileName  = os.path.join(textFolder, "{}{}.fetxt".format(inputName, entry.get_unique_identifier()))
				textDataLabel = "__TEXTPROCESS{:03X}".format(entry.stringId)
				dataFileName = "{}.dmp".format(textFileName)

				# Check if file exists with the same content
				# This is to prevent make to rebuild files that depend on this
				# As it would not have changed

				textNeedsUpdate = True
				textModifyTime = 0.0

				if not forceRefresh:
					if os.path.exists(textFileName):
						textModifyTime = os.path.getmtime(textFileName)

						with open(textFileName, 'r', encoding=OUTPUT_ENCODING) as tf:
							if str(tf.read()) == entry.text:
								textNeedsUpdate = False

					if textModifyTime < timeThreshold:
						textNeedsUpdate = True

				# Write text data

				if textNeedsUpdate:
					if verbose:
						print("TRACE: [write] output `{}`".format(textFileName))

					with open(textFileName, 'w', encoding=OUTPUT_ENCODING) as tf:
						tf.write(entry.text)

				# Write parsed data if we have a parser

				if hasParser:
					if not os.path.exists(dataFileName) or textNeedsUpdate or os.path.getmtime(dataFileName) < textModifyTime:
						if verbose:
							print("TRACE: [write] update `{}`".format(dataFileName))

						generate_text_binary(parserExePath, entry, textFileName, dataFileName)

				# Write include

				f.write("{}:\n".format(textDataLabel))

				if hasParser:
					f.write('#incbin "{}"\n'.format(os.path.relpath(dataFileName, os.path.dirname(outputPath))))
				else:
					f.write('#incext ParseFile "{}"\n'.format(os.path.relpath(textFileName, os.path.dirname(outputPath))))

				f.write("setText(${:X}, {})\n\n".format(entry.stringId, textDataLabel))

			f.write("}\n\n")

			f.write("#endif // TEXT_INSTALLER_{}\n".format(macroizedInputName))

	except ParseFileError as e:
		os.remove(outputPath)
		sys.exit("ERROR: ParseFile errored while parsing text for {}:\n  {}".format(e.textEntry.get_pretty_identifier(), e.errDesc))

	with open(outputDefPath, 'w') as f:
		f.writelines(generate_definitions_lines(macroizedInputName, entryList))

if __name__ == '__main__':
	main(sys.argv[1:])
