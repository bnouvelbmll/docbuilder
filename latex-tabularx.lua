function escapeSpecialChars(text)    
    local rt= text:gsub("%$", "\\$")
    rt = rt:gsub("_", "\\_")
    rt = rt:gsub("&", "\\&")
    rt = rt:gsub("#", "\\#")
    return '{'.. rt ..'}'
    -- return '\\x\\xx {'.. rt ..'}'
    -- return '{\\seqsplit{' .. rt  .. '}}'
end

-- tabularx-filter.lua
function Table(el)
    -- Determine the number of columns by finding the longest row or header
    local num_cols = 0
    if el.headers then
        num_cols = #el.headers
    end
    for _, row in ipairs(el.rows) do
        if #row > num_cols then
            num_cols = #row
        end
    end

    -- Define the column format string, using 'X' for flexible width columns
    local col_format = string.rep("X|", num_cols):sub(1, -2) -- removes the trailing pipe

    -- Start constructing the table with tabularx environment
    local latex_table = {
        pandoc.RawBlock("latex", "\\begin{table}[htbp]"),
        pandoc.RawBlock("latex", "\\begin{tabularx}{\\textwidth}{" .. col_format .. "}"),
        pandoc.RawBlock("latex", "\\hline")
    }

    -- Add the header if exists
    if el.headers and #el.headers > 0 then
        local header_row = {}
        for i, header in ipairs(el.headers) do
            table.insert(header_row, escapeSpecialChars( pandoc.utils.stringify(header)))
        end
        table.insert(latex_table, pandoc.RawBlock("latex", table.concat(header_row, " & ") .. " \\\\ \\hline"))
    end

    -- Inserting the data rows
    for _, row in ipairs(el.rows) do
        local row_cells = {}
        for _, cell in ipairs(row) do
            table.insert(row_cells, escapeSpecialChars( pandoc.utils.stringify(cell)))
        end
        table.insert(latex_table, pandoc.RawBlock("latex", table.concat(row_cells, " & ") .. " \\\\ \\hline"))
    end

    -- Close the tabularx and table environments
    table.insert(latex_table, pandoc.RawBlock("latex", "\\end{tabularx}"))
    table.insert(latex_table, pandoc.RawBlock("latex", "\\end{table}"))

    -- Replace the original table element with the new RawBlock elements
    return latex_table
end


function escapeSpecialSymbols(text)
    text = text:gsub('{', '\\{') -- Escape open brace
    text = text:gsub('}', '\\}') -- Escape close brace
    text = text:gsub('\\[^\\{}]', '\\textbackslash{}') -- Escape backslash
    text = text:gsub('%%', '\\%%') -- Escape percent signs
    text = text:gsub('&', '\\&') -- Escape ampersand
    text = text:gsub('_', '\\_') -- Escape underscore
    text = text:gsub('#', '\\#') -- Escape hash
    text = text:gsub('%$', '\\$') -- Escape dollar
    
    return text
end

function processTableHeadersOld(headers)
    if not headers then return "" end  -- Ensure there is a header to process
    local processed_headers = {}
    for i, header in ipairs(headers) do
        if header and header.content then
            local header_text = pandoc.utils.stringify(header.content)  -- Convert header content to string
            local escaped_header = escapeSpecialSymbols(header_text)  -- Escape LaTeX special characters
            table.insert(processed_headers, escaped_header)
        else
            table.insert(processed_headers, "")  -- Insert empty string if header content is missing
        end
    end
    return table.concat(processed_headers, " & ")
end

function processTableHeaders(head)
    if not head or #head == 0 then return "" end  -- Ensure there is a head with content

    local headerRows = {}
    for _, row in ipairs(head) do
        local cells = {}
        for _, cell in ipairs(row) do
            local cellText = pandoc.utils.stringify(cell.content)  -- Convert cell content to string
            local escapedCellText = escapeSpecialChars(cellText)  -- Escape LaTeX special characters            
            table.insert(cells, "\\textbf{".. escapedCellText.."}")
        end
        table.insert(headerRows, table.concat(cells, ", "))
    end
    local r= table.concat(headerRows, " & ")
    return r
end


function Code(elem)
    -- Wrap the code text with the custom LaTeX command \code{}
    local text = "\\code{" .. escapeSpecialSymbols(elem.text) .. "}\\iffalse "    
    return pandoc.Span({ pandoc.RawInline('latex', text),pandoc.Str(escapeSpecialSymbols(elem.text)), pandoc.RawInline('latex', "\\fi") })
end


function handleTableCellContentO(cell)
    local parts = {}
    
    if cell.content  then 
        for _, content in ipairs(cell.content) do            
            table.insert(parts, handleTableCellContent(content))
            -- print("S")
        end
    end
    if not (cell.t == nil) then
        -- table.insert(parts, cell)
    -- if cell.t == "Code" then
    --     -- Handle code elements, wrapping them in \texttt and escaping necessary characters
    --     -- return Code(cell)
        if not (cell.text == nil) then
           print("C " .. cell.t .. ' ' ..cell.text)
           -- table.insert(parts, "\\autosize{" .. escapeSpecialSymbols(cell.text)..'}')
           table.insert(parts,' '..cell.text)
        end
    else
        -- Use stringify for other elements and escape as usual
        if cell.text then
            print("T"..cell.text)
            table.insert(parts, escapeSpecialSymbols(cell.text))
        else
            if not (cell.t == nil) then 
               -- print("TE", cell.t)
               table.insert(parts, cell)
            else
                -- print("TF")
                table.insert(parts,  escapeSpecialSymbols(pandoc.utils.stringify(cell)))
            end
        end
    end
    return table.concat(parts)
end

function handleTableCellContent(cell)
    local parts = {}
    -- Recursively handle nested contents if present
    if cell.content then
        for _, innerContent in ipairs(cell.content) do
            local processedText = handleTableCellContent(innerContent)
            -- Ensure there is space between elements, but only if there is something to add
            if processedText ~= "" then
                table.insert(parts, processedText)
            end
        end
        return table.concat(parts)
    end

    -- -- Handle the text directly if present
    if cell.text then
         --print("Processing text: " .. cell.t .. ' ' .. cell.text)
         
         local escapedText = cell.text
         if not (cell.t == 'RawInline') then
            escapedText  = escapeSpecialSymbols(cell.text)
         end
    --     -- Append with a preceding space to maintain separation, conditionally
        if #parts > 0 then
            table.insert(parts, ' ' .. escapedText)
        else
            table.insert(parts, escapedText)
        end
        -- return escapeSpecialSymbols(pandoc.utils.stringify(cell))
    elseif cell.t and not cell.text and cell.t ~= "Space" then
         -- This branch handles non-text elements that might be present; adjust as necessary
        -- print("Non-text cell type detected: ", cell.t)
        table.insert(parts, pandoc.utils.stringify(cell))
    else
        table.insert(parts, " ")
    end

    return table.concat(parts)
end


function handleTableCells(cell)
    -- Handle different content blocks within the cell
    local parts = {}
    for _, content in ipairs(cell) do
        table.insert(parts, handleTableCellContent(content))
    end
    return table.concat(parts)
end


function concatenateRawBlocks(rawBlocks)
    -- Initialize an empty string to hold the concatenated content
    local combined_content = ""

    -- Iterate through the Lua table of RawBlock elements
    for _, rawBlock in ipairs(rawBlocks) do
        if rawBlock.t == "RawBlock" and rawBlock.format == "latex" then
            -- Append the text of each RawBlock to the combined_content, adding a newline for separation
            combined_content = combined_content .. rawBlock.text .. "\n"
        end
    end

    -- Create a new RawBlock with the concatenated content
    return pandoc.RawBlock("latex", combined_content)
end

-- supertabular-filter.lua
function TableSupertabular(el)
    -- Determine the number of columns by finding the longest row or header
    local num_cols = 0
    if el.headers then
        num_cols = #el.headers
    end
    for _, row in ipairs(el.rows) do
        if #row > num_cols then
            num_cols = #row
        end
    end

    -- Define the column format string, using 'l' for left-aligned columns
    -- local col_format = string.rep("l|", num_cols):sub(1, -2)  -- removes the trailing pipe

    -- Define the width of each column
    -- local col_width = "\\dimexpr \\textwidth/" .. num_cols .. "\\relax"
    -- Sum lengths of each cell in each column and count entries
    local sums = {}
    local counts = {}
    local maxWordLengths = {}
    for i = 1, num_cols do
        sums[i] = 0
        counts[i] = 0
        maxWordLengths[i] = 0
    end 

    for _, row in ipairs(el.rows) do
        for i, cell in ipairs(row) do
            local text = pandoc.utils.stringify(cell)
            sums[i] = sums[i] + string.len(text)
            counts[i] = counts[i] + 1
            for word in string.gmatch(text, "%w+") do
                maxWordLengths[i] = math.max(maxWordLengths[i], string.len(word))
            end
        end
    end

    -- Compute square root of the average length for each column
    local weights = {}
    local weights2 = {}
    for i = 1, num_cols do
        local average = sums[i] / counts[i]
        weights[i] = math.sqrt(average)
        weights2[i] = math.sqrt(maxWordLengths[i])
    end

    -- Sum of all weights to normalize
    local total_weight = 0
    local total_weight2 = 0
    for i = 1, num_cols do
        total_weight = total_weight + weights[i]
        total_weight2 = total_weight2 + weights2[i]
    end

    -- Define the column format string, using calculated weights
    local col_format = ""
    for i = 1, num_cols do
        local width = ((weights[i] / total_weight) + (weights2[i] / total_weight2)) * 49.99 * 0.9  -- percentage of text width
        width = math.floor(width * 10^2 + 0.5) / 10^4
        col_format = col_format .. "p{" .. tostring(width) .. "\\textwidth}|"
    end
    col_format = col_format:sub(1, -2)  -- removes the trailing pipe

    -- Define the column format string, using 'p{width}' for paragraph columns
--    local col_format = string.rep("p{" .. col_width .. "}|", num_cols):sub(1, -2)  -- removes the trailing pipe
    local header_content = processTableHeaders(el.headers)
    -- Start constructing the table with supertabular environment
    local latex_table = {
        pandoc.RawBlock("latex", "\\nobreak"), -- fix v overflow
        -- pandoc.RawBlock("latex", "\\begin{minipage}{\\textwidth}"), -- fix v overflow
        pandoc.RawBlock("latex", "\\begin{small}"),
        pandoc.RawBlock("latex", "\\tablefirsthead{\\hline \\rowcolor{headercolor1}  " .. header_content .. " \\\\ \\hline}"), -- tableHeaders
        pandoc.RawBlock("latex", "\\tablehead{\\hline \\rowcolor{headercolor2} \\multicolumn{" .. num_cols .. "}{|c|}{\\small\\slshape continued from previous page} \\\\ \\hline \\rowcolor{headercolor1}" .. header_content .. " \\\\ \\hline}"),
        pandoc.RawBlock("latex", "\\tabletail{\\hline \\rowcolor{headercolor2} \\multicolumn{" .. num_cols .. "}{|r|}{\\small\\slshape continued on next page} \\\\ \\hline}"),
        pandoc.RawBlock("latex", "\\tablelasttail{\\hline}"),        
        pandoc.RawBlock("latex", "\\begin{supertabular}{" .. col_format .. "}"),
        pandoc.RawBlock("latex", "\\hline")
    }

    -- -- Add the header if exists
    -- if el.headers and #el.headers > 0 then
    --     local header_row = {}
    --     for _, header in ipairs(el.headers) do
    --         local escaped_header = escapeLatexSpecialChars(pandoc.utils.stringify(header))
    --         table.insert(header_row, escaped_header)
    --     end
    --     table.insert(latex_table, pandoc.RawBlock("latex", table.concat(header_row, " & ") .. " \\\\ \\hline"))
    -- end



    -- -- Start constructing the table with supertabular environment
    -- local latex_table = {
        
    --     --pandoc.RawBlock("latex", "\\tablehead{\\hline \\multicolumn{" .. num_cols .. "}{|c|}{\\small\\sl continued from previous page} \\\\ \\hline " .. tableHeaders(el.headers) .. " \\\\ \\hline}"),
    --     --pandoc.RawBlock("latex", "\\tabletail{\\hline \\multicolumn{" .. num_cols .. "}{|r|}{\\small\\sl continued on next page} \\\\ \\hline}"),
    --     --pandoc.RawBlock("latex", "\\tablelasttail{\\hline}"),
    --     --pandoc.RawBlock("latex", "\\begin{supertabular}{" .. col_format .. "}")
    --     pandoc.RawBlock("latex", "\\tablelasttail{\\hline}"),
    --     pandoc.RawBlock("latex", "\\begin{supertabular}{" .. col_format .. "}")
         
    -- }

    -- Inserting the data rows
    -- for _, row in ipairs(el.rows) do
    --     local row_cells = {}
    --     for _, cell in ipairs(row) do
    --         table.insert(row_cells, escapeSpecialSymbols(pandoc.utils.stringify(cell)))
    --     end
    --     table.insert(latex_table, pandoc.RawBlock("latex", table.concat(row_cells, " & ") .. " \\\\"))
    -- end

  
    for _, row in ipairs(el.rows) do
        local row_cells = {}
        for _, cell in ipairs(row) do
            table.insert(row_cells, handleTableCells(cell))
        end
        table.insert(latex_table, pandoc.RawBlock("latex", table.concat(row_cells, " & ") .. " \\\\"))
    end


    -- Close the supertabular environment
    table.insert(latex_table, pandoc.RawBlock("latex", "\\end{supertabular}"))
    table.insert(latex_table, pandoc.RawBlock("latex", "\\end{small}"))
    -- table.insert(latex_table, pandoc.RawBlock("latex", "\\end{minipage}"))

    -- Replace the original table element with the new RawBlock elements
    return concatenateRawBlocks(latex_table)
end

-- Function to convert headers to a LaTeX row
function tableHeaders(headers)
    if headers then
        local header_row = {}
        for i, header in ipairs(headers) do
            table.insert(header_row, pandoc.utils.stringify(header))
        end
        return table.concat(header_row, " & ")
    else
        return ""
    end
end



-- LaTeX commands to be handled (matching definitions needed!)
local latexCmds = pandoc.List:new {'alert', 'code', 'autosize'}

-- LaTeX environments to be handled (matching definitions needed!)
local latexEnvs = pandoc.List:new { 'center', 'vfix', 'landscape', 'xlandscape', 'internaldocs'}

-- handle selected Spans: embed content into a RawInline with matching LaTeX command
function Span(el)
    local cmd = el.classes[1]

    -- should we handle this command?
    if latexCmds:includes(cmd) then
        return {pandoc.RawInline("latex", "\\" .. cmd .. "{")} .. el.content .. {pandoc.RawInline("latex", "}")}
    end
end

-- handle selected Divs: embed content into a RawBlock with matching LaTeX environment
function Div(el)
    local env = el.classes[1]
    print("div: " .. env)

    -- should we handle this environment?
    if latexEnvs:includes(env) then
        return {pandoc.RawBlock("latex", "\\begin{" .. env .. "}")} .. el.content .. {pandoc.RawBlock("latex", "\\end{" .. env .. "}")}
    end
end


-- center images without captions too (like "real" images w/ caption aka figures)
--
-- remove as a precaution a possibly existing parameter `web_width`, which
-- should only be respected in the web version.
--
-- note: images w/ caption will be parsed (implicitly) as figures instead - no need to check for empty caption here
function Image(el)
    el.attributes["web_width"] = nil
    return { pandoc.RawInline('latex', '\\begin{center}'), el, pandoc.RawInline('latex', '\\end{center}') }
end


-- wrap inline code in `inlinecode` LaTeX command
-- function Code(el)
--     return { pandoc.RawInline("latex", "\\inlinecode{"), el, pandoc.RawInline("latex", "}") }
-- end


-- wrap listings (code block) in `codeblock` LaTeX environment
-- set font size to "small" (default) or use attribute "size"
function CodeBlock(el)
    local size = el.attributes.size or "small"
    return { pandoc.RawBlock("latex", "\\" .. size),
             pandoc.RawBlock("latex", "\\begin{codeblock}"),
             el,
             pandoc.RawBlock("latex", "\\end{codeblock}"),
             pandoc.RawBlock("latex", "\\normalsize") }
end


-- -- do not remove "`el`{=markdown}", convert it to raw "LaTeX" instead
-- -- see https://github.com/KI-Vorlesung/kitest/issues/80
-- function RawInline(el)
--     if el.format:match 'markdown' then
--         return pandoc.RawInline('latex', el.text)
--     end
-- end
  
return {{Table = TableSupertabular, Code=Code, CodeBlock=CodeBlock, Image=Image, Span=Span, Div=Div}}

