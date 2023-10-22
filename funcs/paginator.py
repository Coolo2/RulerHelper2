
import discord
import typing

class PaginatorView(discord.ui.View):

    def __init__(
                self, 
                embed : discord.Embed, 
                text : str = None, 
                split_character : str = "\n", 
                per_page : int = 10, 
                index : int = 0, 
                private = None, 
                page_image_generators : typing.List[typing.Tuple[typing.Callable, tuple]] = [],
                search : bool = True
    ):
        self.embed = embed
        self.index = index
        self.private : discord.User = private
        self.page_image_generators = page_image_generators
        self.attachment = None

        if len(page_image_generators) > 0 and page_image_generators[0]:
            generator = self.page_image_generators[self.index]
            
            if type(generator) == str:
                embed.set_image(url=generator)
            else:
                image = generator[0](*generator[1])
                graph = discord.File(image, filename="paginator_image.png")
                self.attachment = graph
                embed.set_image(url="attachment://paginator_image.png")

        if not text:
            text = (embed.description + split_character) * len(page_image_generators) if embed.description else split_character.join(["_ _"]*len(page_image_generators))
            per_page = embed.description.count(split_character)+1
        
        pages = text.split(split_character)
        if "" in pages:
            pages.remove("")
        
        self.pages = [split_character.join(pages[i:i+per_page]) for i in range(0, len(pages), per_page)]
        self.embed.description = self.pages[0] if len(pages) > 0 else "_ _"

        if self.embed.footer.text and "Page " not in self.embed.footer.text:
            self.embed.set_footer(text=f"{self.embed.footer.text} - Page {self.index+1}/{len(self.pages)}")
        else:
            self.embed.set_footer(text=f"Page {self.index+1}/{len(self.pages)}")

        super().__init__(timeout=1800)

        self.children[1].disabled = self.index >= len(self.pages) - 1
        self.children[0].disabled = self.index <= 0

        if not search:
            self.remove_item(self.children[2])
        
    
    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="◀️", disabled=True)
    async def _left(self, interaction : discord.Interaction, button: discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 

        embed = self.embed 

        self.index -= 1
        embed.description = self.pages[self.index]

        self.children[1].disabled = self.index >= len(self.pages) - 1
        self.children[0].disabled = self.index <= 0

        embed.set_footer(text=embed.footer.text.replace(f"Page {self.index+2}", f"Page {self.index+1}"))

        if len(self.page_image_generators)-1 >= self.index and self.page_image_generators[self.index] and self.page_image_generators[self.index] != self.page_image_generators[self.index+1]:
            generator = self.page_image_generators[self.index]
            
            if type(generator) == str:
                embed.set_image(url=generator)
            else:
                image = generator[0](*generator[1])
                graph = discord.File(image, filename="paginator_image.png")
                embed.set_image(url="attachment://paginator_image.png")

                return await interaction.response.edit_message(embed=embed, view=self, attachments=[graph])
            
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="▶️")
    async def _right(self, interaction : discord.Interaction, button: discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 
        
        embed = self.embed 

        self.index += 1
        embed.description = self.pages[self.index]

        self.children[1].disabled = self.index >= len(self.pages) - 1
        self.children[0].disabled = self.index <= 0

        embed.set_footer(text=embed.footer.text.replace(f"Page {self.index}", f"Page {self.index+1}"))

        if len(self.page_image_generators)-1 >= self.index and self.page_image_generators[self.index] and self.page_image_generators[self.index] != self.page_image_generators[self.index-1]:
            generator = self.page_image_generators[self.index]

            if type(generator) == str:
                embed.set_image(url=generator)
            else:
                image = generator[0](*generator[1])
                graph = discord.File(image, filename="paginator_image.png")
                embed.set_image(url="attachment://paginator_image.png")

                return await interaction.response.edit_message(embed=embed, view=self, attachments=[graph])
            
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="🔎")
    async def _search(self, interaction : discord.Interaction, button : discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 

        await interaction.response.send_modal(SearchModal(self))

class SearchModal(discord.ui.Modal):

    def __init__(self, paginator : PaginatorView):

        self.paginator = paginator

        super().__init__(title="Search", timeout=None)
    
    query = discord.ui.TextInput(placeholder='Enter search query here', label="Search Query", required=True, style=discord.TextStyle.short)

    async def on_submit(self, interaction : discord.Interaction):

        for i, page in enumerate(self.paginator.pages):
            
            if self.query.value.lower() in page.lower():
                embed = self.paginator.embed 

                prevIndex = self.paginator.index

                self.paginator.index = i
                embed.description = self.paginator.pages[self.paginator.index]

                self.paginator.children[1].disabled = self.paginator.index >= len(self.paginator.pages) - 1
                self.paginator.children[0].disabled = self.paginator.index <= 0

                embed.set_footer(text=embed.footer.text.replace(f"Page {prevIndex+1}", f"Page {self.paginator.index+1}"))
                    
                return await interaction.response.edit_message(embed=embed, view=self.paginator)
        
        return await interaction.response.send_message("Search query not found.", ephemeral=True)